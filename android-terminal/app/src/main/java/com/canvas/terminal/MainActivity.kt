package com.canvas.terminal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import jackpal.androidterm.emulatorview.EmulatorView
import jackpal.androidterm.emulatorview.TermSession
import jackpal.androidterm.emulatorview.UpdateCallback
import jackpal.androidterm.util.TermSettings
import jackpal.androidterm.session.ShellTermSession

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { App() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun App() {
    MaterialTheme(colorScheme = darkScheme()) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
            TerminalScreen()
        }
    }
}

@Composable
fun TerminalScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current

    // Terminal settings
    val settings = remember {
        TermSettings(context.resources, context.packageName).apply {
            // Defaults; can be extended to preferences
        }
    }

    // Term session
    var session by remember { mutableStateOf<TermSession?>(null) }
    var emulatorView by remember { mutableStateOf<EmulatorView?>(null) }

    LaunchedEffect(Unit) {
        val shell = System.getenv("SHELL") ?: "/system/bin/sh"
        val termSession = ShellTermSession(settings, shell, null)
        session = termSession
    }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        TopAppBar(title = { Text("Canvas Terminal") })
        Box(
            modifier = Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant),
            contentAlignment = Alignment.TopStart
        ) {
            AndroidTerminal(session) { emulatorView = it }
        }
    }
}

@Composable
fun AndroidTerminal(session: TermSession?, onReady: (EmulatorView) -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    AndroidView(factory = { ctx ->
        EmulatorView(ctx).apply {
            setTextSize(14)
            setUseCookedIME(true)
            setKeepScreenOn(true)
        }
    }, update = { view ->
        if (session != null && view.session != session) {
            view.attachSession(session)
            onReady(view)
            session.setUpdateCallback(object : UpdateCallback {
                override fun onUpdate() { view.invalidate() }
            })
        }
    }, modifier = Modifier.fillMaxSize())
}

fun darkScheme(): ColorScheme = darkColorScheme(
    primary = Color(0xFFA3BFFA),
    onPrimary = Color(0xFF0F1115),
    surface = Color(0xFF141821),
    surfaceVariant = Color(0xFF1B2130),
    onSurface = Color(0xFFE6EAF2),
)
