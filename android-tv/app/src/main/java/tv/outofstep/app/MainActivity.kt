package tv.outofstep.app

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout

/**
 * OutofStep.tv for Android TV, Google TV and Fire TV.
 * The app is a full-screen window onto the live site (same catalog, same updates),
 * with the remote's Back and media buttons handed to the site's own TV controls.
 */
class MainActivity : Activity() {

    companion object {
        const val HOME = "https://nj908crew.github.io/tv/"
        const val HOST = "nj908crew.github.io"
    }

    private lateinit var web: WebView
    private var customView: View? = null
    private var customCallback: WebChromeClient.CustomViewCallback? = null
    private lateinit var root: FrameLayout

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        hideSystemBars()

        root = FrameLayout(this)
        web = WebView(this)
        web.setBackgroundColor(Color.parseColor("#0B0C0E"))
        root.addView(web, FrameLayout.LayoutParams(-1, -1))
        setContentView(root)

        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            loadWithOverviewMode = true
            useWideViewPort = true
            // Tells the site to switch into its TV layout and remote controls.
            userAgentString = "$userAgentString OutofStepTV/1.0 AndroidTV"
        }
        web.isFocusable = true
        web.isFocusableInTouchMode = true

        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url
                if (url.host == HOST || url.scheme == "file") return false
                // Anything else (e.g. "Watch on YouTube") opens in the TV's own app.
                try { startActivity(Intent(Intent.ACTION_VIEW, url)) } catch (_: Exception) {}
                return true
            }

            override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                if (request.isForMainFrame) view.loadUrl("file:///android_asset/offline.html")
            }
        }

        // Lets embedded players go full screen if they ask to.
        web.webChromeClient = object : WebChromeClient() {
            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                customView = view; customCallback = callback
                root.addView(view, FrameLayout.LayoutParams(-1, -1))
                web.visibility = View.GONE
            }

            override fun onHideCustomView() {
                customView?.let { root.removeView(it) }
                customView = null
                web.visibility = View.VISIBLE
                customCallback?.onCustomViewHidden()
            }
        }

        if (savedInstanceState != null) web.restoreState(savedInstanceState) else web.loadUrl(HOME)
        web.requestFocus()
    }

    private fun hideSystemBars() {
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION)
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    /** Media buttons on the remote go straight to the site's player. */
    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        val action = when (event.keyCode) {
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE -> "pp"
            KeyEvent.KEYCODE_MEDIA_PLAY -> "play"
            KeyEvent.KEYCODE_MEDIA_PAUSE -> "pause"
            KeyEvent.KEYCODE_MEDIA_STOP -> "stop"
            KeyEvent.KEYCODE_MEDIA_FAST_FORWARD -> "ff"
            KeyEvent.KEYCODE_MEDIA_REWIND -> "rw"
            KeyEvent.KEYCODE_MEDIA_NEXT -> "next"
            KeyEvent.KEYCODE_MEDIA_PREVIOUS -> "prev"
            else -> null
        }
        if (action != null) {
            if (event.action == KeyEvent.ACTION_UP) {
                web.evaluateJavascript("window.__tvKey && window.__tvKey('$action')", null)
            }
            return true
        }
        return super.dispatchKeyEvent(event)
    }

    /** Back steps out one level inside the site; at the top level it leaves the app. */
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (customView != null) { web.webChromeClient?.onHideCustomView(); return }
        web.evaluateJavascript("(window.__tvBack ? window.__tvBack() : false)") { handled ->
            if (handled != "true") {
                if (web.url?.startsWith("file:") == true) finish()
                else if (handled == "null" && web.canGoBack()) web.goBack()
                else finish()
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    override fun onPause() { super.onPause(); web.onPause() }
    override fun onResume() { super.onResume(); web.onResume(); hideSystemBars() }
    override fun onDestroy() { web.destroy(); super.onDestroy() }
}
