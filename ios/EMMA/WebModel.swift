/*
* Copyright 2026 The Board of Trustees of the University of Illinois. All Rights Reserved.
* Licensed under the terms of the MIT License (the "License")
* The License is included in the distribution as License file.
* You may not use this file except in compliance with the License. 
* Software distributed under the License is distributed on an "AS IS" BASIS,  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
* See the License file for the specific language governing permissions and limitations under the License. 
*/

import Observation
import SwiftUI
import WebKit

/// Owns the web view: loads the home page, keeps the title and Back button up
/// to date, hides the campus header and footer, and opens links to other
/// websites in Safari.
@MainActor
@Observable
final class WebModel: NSObject, WKNavigationDelegate {
    /// The first page: web/index.html.
    static let homeURL = URL(string: "\(ContentSchemeHandler.scheme)://\(ContentSchemeHandler.appHost)/index.html")!

    /// On iOS the pages have no campus header or footer (the web app shows them).
    private static let hideHeaderAndFooter = """
        (function () {
          var style = document.createElement("style");
          style.textContent = "ilw-header, ilw-footer { display: none !important; }";
          var add = function () { (document.head || document.documentElement).appendChild(style); };
          if (document.documentElement) { add(); } else { document.addEventListener("DOMContentLoaded", add); }
        })();
        """

    let webView: WKWebView
    var title = "EMMA"
    var canGoBack = false

    @ObservationIgnored private var observations: [NSKeyValueObservation] = []

    override init() {
        let configuration = WKWebViewConfiguration()
        configuration.setURLSchemeHandler(ContentSchemeHandler(), forURLScheme: ContentSchemeHandler.scheme)
        configuration.userContentController.addUserScript(WKUserScript(
            source: Self.hideHeaderAndFooter, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()

        webView.navigationDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        observations = [
            webView.observe(\.title, options: [.new]) { [weak self] webView, _ in
                MainActor.assumeIsolated {
                    let title = webView.title ?? ""
                    // Page titles end with " | EMMA"; the bar only needs the page's own name.
                    self?.title = title.isEmpty ? "EMMA" : title.replacingOccurrences(of: " | EMMA", with: "")
                }
            },
            webView.observe(\.canGoBack, options: [.new]) { [weak self] webView, _ in
                MainActor.assumeIsolated {
                    self?.canGoBack = webView.canGoBack
                }
            },
        ]
        goHome()
    }

    func goHome() {
        webView.load(URLRequest(url: Self.homeURL))
    }

    func goBack() {
        webView.goBack()
    }

    // Links to other websites, email addresses and phone numbers open outside the app.
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction) async -> WKNavigationActionPolicy {
        if navigationAction.navigationType == .linkActivated,
           let url = navigationAction.request.url,
           ["http", "https", "mailto", "tel"].contains(url.scheme?.lowercased() ?? "") {
            await UIApplication.shared.open(url)
            return .cancel
        }
        return .allow
    }
}
