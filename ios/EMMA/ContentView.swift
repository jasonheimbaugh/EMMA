/*
* Copyright 2026 The Board of Trustees of the University of Illinois. All Rights Reserved.
* Licensed under the terms of the MIT License (the "License")
* The License is included in the distribution as License file.
* You may not use this file except in compliance with the License. 
* Software distributed under the License is distributed on an "AS IS" BASIS,  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
* See the License file for the specific language governing permissions and limitations under the License. 
*/

import SwiftUI
import WebKit

/// The app's one screen: a page from web/, with Back and Home buttons and the
/// page's title in the navigation bar.
struct ContentView: View {
    @State private var model = WebModel()

    var body: some View {
        NavigationStack {
            WebView(webView: model.webView)
                .ignoresSafeArea(edges: .bottom)
                .navigationTitle(model.title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            model.goBack()
                        } label: {
                            Image(systemName: "chevron.backward")
                        }
                        .disabled(!model.canGoBack)
                        .accessibilityLabel("Back")
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            model.goHome()
                        } label: {
                            Image(systemName: "house")
                        }
                        .accessibilityLabel("Home")
                    }
                }
        }
    }
}

/// Puts the model's WKWebView into SwiftUI.
struct WebView: UIViewRepresentable {
    let webView: WKWebView

    func makeUIView(context: Context) -> WKWebView { webView }
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}

#Preview {
    ContentView()
}
