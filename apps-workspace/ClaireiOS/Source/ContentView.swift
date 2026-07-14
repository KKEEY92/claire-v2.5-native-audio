import SwiftUI
import WebKit

struct ContentView: View {
    @State private var backendURL: String = "http://192.168.178.179:8550" // Lokaler Standard, anpassbar

    var body: some View {
        VStack(spacing: 0) {
            WebView(url: URL(string: backendURL)!)
                .edgesIgnoringSafeArea(.all)
        }
        .onAppear {
            // Optional: Lies die URL aus einer config-Datei oder Umgebung
            if let configURL = Bundle.main.object(forInfoDictionaryKey: "CLAIRE_BACKEND_URL") as? String, !configURL.isEmpty {
                backendURL = configURL
            }
        }
    }
}

struct WebView: UIViewRepresentable {
    let url: URL

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        // Keine Updates nötig
    }
}
