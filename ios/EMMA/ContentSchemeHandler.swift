/*
* Copyright 2026 The Board of Trustees of the University of Illinois. All Rights Reserved.
* Licensed under the terms of the MIT License (the "License")
* The License is included in the distribution as License file.
* You may not use this file except in compliance with the License. 
* Software distributed under the License is distributed on an "AS IS" BASIS,  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
* See the License file for the specific language governing permissions and limitations under the License. 
*/

import Foundation
import UniformTypeIdentifiers
import WebKit

/// Serves the app's pages to the web view at emma://app/..., from the web/
/// folder built into the app, so they load with no network.
///
/// The pages load the Illinois Web Components Toolkit with addresses that start
/// with "//" (for example //cdn.toolkit.illinois.edu/3/toolkit.js). In the app
/// those become emma://cdn.toolkit.illinois.edu/..., which this handler fetches
/// over https and saves in the app's Caches folder. When there is no network,
/// it serves the saved copy, so after the app has been opened once online the
/// toolkit works offline too.
final class ContentSchemeHandler: NSObject, WKURLSchemeHandler {
    static let scheme = "emma"
    static let appHost = "app"

    private let root: URL = Bundle.main.url(forResource: "web", withExtension: nil)!
    private let cache: URL = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("cdn", isDirectory: true)
    private let session: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 10
        return URLSession(configuration: configuration)
    }()

    /// Tasks the web view has stopped; WebKit must not hear about them again.
    private var stopped = Set<ObjectIdentifier>()

    func webView(_ webView: WKWebView, start task: WKURLSchemeTask) {
        guard let url = task.request.url, let host = url.host() else {
            task.didFailWithError(URLError(.badURL))
            return
        }
        if host == Self.appHost {
            serveFile(url, to: task)
        } else {
            serveRemote(url, host: host, to: task)
        }
    }

    func webView(_ webView: WKWebView, stop task: WKURLSchemeTask) {
        stopped.insert(ObjectIdentifier(task))
    }

    // MARK: Pages from web/

    private func serveFile(_ url: URL, to task: WKURLSchemeTask) {
        var path = url.path(percentEncoded: false)
        if path.isEmpty || path.hasSuffix("/") {
            path += "index.html"  // iap/ is iap/index.html, as on a web server
        }
        var file = root.appendingPathComponent(path).standardizedFileURL
        var isDirectory: ObjCBool = false
        if FileManager.default.fileExists(atPath: file.path, isDirectory: &isDirectory), isDirectory.boolValue {
            file.appendPathComponent("index.html")
        }
        // Never serve anything outside web/.
        guard file.path.hasPrefix(root.standardizedFileURL.path + "/"),
              let data = try? Data(contentsOf: file) else {
            respond(to: task, url: url, status: 404, mimeType: "text/plain", data: Data("Not found".utf8))
            return
        }
        respond(to: task, url: url, status: 200, mimeType: Self.mimeType(for: file), data: data)
    }

    // MARK: Toolkit and other CDN files

    private func serveRemote(_ url: URL, host: String, to task: WKURLSchemeTask) {
        var components = URLComponents(url: url, resolvingAgainstBaseURL: false)!
        components.scheme = "https"
        guard let remote = components.url else {
            task.didFailWithError(URLError(.badURL))
            return
        }
        var path = url.path(percentEncoded: false)
        if path.isEmpty || path.hasSuffix("/") {
            path += "index"
        }
        let saved = cache.appendingPathComponent(host, isDirectory: true).appendingPathComponent(path)

        session.dataTask(with: remote) { data, response, _ in
            let http = response as? HTTPURLResponse
            Task { @MainActor in
                if let data, let http, http.statusCode == 200 {
                    let mimeType = http.mimeType ?? Self.mimeType(for: saved)
                    try? FileManager.default.createDirectory(
                        at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                    try? data.write(to: saved, options: .atomic)
                    self.respond(to: task, url: url, status: 200, mimeType: mimeType, data: data)
                } else if let data = try? Data(contentsOf: saved) {
                    self.respond(to: task, url: url, status: 200, mimeType: Self.mimeType(for: saved), data: data)
                } else {
                    self.respond(to: task, url: url, status: http?.statusCode ?? 504,
                                 mimeType: "text/plain", data: Data("Not available offline".utf8))
                }
            }
        }.resume()
    }

    // MARK: Responses

    private func respond(to task: WKURLSchemeTask, url: URL, status: Int, mimeType: String, data: Data) {
        guard !stopped.contains(ObjectIdentifier(task)) else { return }
        let headers = [
            "Content-Type": mimeType,
            "Content-Length": String(data.count),
            // The toolkit is a JavaScript module from another host (emma://cdn...),
            // which WebKit loads only with this header.
            "Access-Control-Allow-Origin": "*",
        ]
        let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: "HTTP/1.1", headerFields: headers)!
        task.didReceive(response)
        task.didReceive(data)
        task.didFinish()
    }

    private static func mimeType(for file: URL) -> String {
        switch file.pathExtension.lowercased() {
        case "html", "htm": return "text/html"
        case "js", "mjs": return "text/javascript"
        case "css": return "text/css"
        case "json": return "application/json"
        case "svg": return "image/svg+xml"
        case "png": return "image/png"
        case "woff2": return "font/woff2"
        case "woff": return "font/woff"
        default:
            return UTType(filenameExtension: file.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        }
    }
}
