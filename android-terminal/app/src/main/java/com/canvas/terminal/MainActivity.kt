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
import androidx.compose.material3.darkColorScheme
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

@Composable
fun App() {
    MaterialTheme(colorScheme = darkColorScheme(
        primary = Color(0xFFA3BFFA),
        onPrimary = Color(0xFF0F1115),
        surface = Color(0xFF141821),
        surfaceVariant = Color(0xFF1B2130),
        onSurface = Color(0xFFE6EAF2),
    )) {
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) { TerminalScreen() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TerminalScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val settings = remember { TermSettings(context.resources, context.packageName) }
    var session by remember { mutableStateOf<TermSession?>(null) }

    LaunchedEffect(Unit) {
        val shell = System.getenv("SHELL") ?: "/system/bin/sh"
        session = ShellTermSession(settings, shell, null)
    }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        TopAppBar(title = { Text("Canvas Terminal") })
        Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surfaceVariant)) {
            AndroidTerminal(session)
        }
    }
}

@Composable
fun AndroidTerminal(session: TermSession?) {
    AndroidView(factory = { ctx ->
        EmulatorView(ctx).apply {
            setTextSize(14)
            setUseCookedIME(true)
            setKeepScreenOn(true)
        }
    }, update = { view ->
        if (session != null && view.session != session) {
            view.attachSession(session)
            session.setUpdateCallback(object : UpdateCallback {
                override fun onUpdate() { view.invalidate() }
            })
        }
    }, modifier = Modifier.fillMaxSize())
}
