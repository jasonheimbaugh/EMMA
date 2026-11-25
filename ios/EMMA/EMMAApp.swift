/*
* Copyright 2026 The Board of Trustees of the University of Illinois. All Rights Reserved.
* Licensed under the terms of the MIT License (the "License")
* The License is included in the distribution as License file.
* You may not use this file except in compliance with the License. 
* Software distributed under the License is distributed on an "AS IS" BASIS,  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
* See the License file for the specific language governing permissions and limitations under the License. 
*/

import SwiftUI

/// EMMA for iOS: shows the web app's pages (the web/ folder, built into the
/// app) in a web view, without the campus header and footer.
@main
struct EMMAApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
