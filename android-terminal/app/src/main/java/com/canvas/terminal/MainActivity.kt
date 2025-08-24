package com.canvas.terminal

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.material3.darkColorScheme

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
        Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.surface) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Canvas Terminal – Android shell coming next")
            }
        }
    }
}
