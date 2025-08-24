plugins { id("com.android.library"); id("org.jetbrains.kotlin.android") }
android {
  namespace = "jackpal.androidterm"
  compileSdk = 34
  defaultConfig { minSdk = 26; targetSdk = 34 }
  sourceSets["main"].java.srcDirs("src/main/java")
  sourceSets["main"].manifest.srcFile("src/main/AndroidManifest.xml")
  sourceSets["main"].res.srcDirs("src/main/res")
  compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
  kotlinOptions { jvmTarget = "17" }
}
dependencies { implementation(project(":third_party:emulatorview")) }
