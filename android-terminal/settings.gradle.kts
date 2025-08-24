pluginManagement {
  repositories {
    google()
    mavenCentral()
    gradlePluginPortal()
    maven(url = uri("https://jitpack.io"))
  }
}
dependencyResolutionManagement {
  repositoriesMode.set(RepositoriesMode.PREFER_SETTINGS)
  repositories {
    google()
    mavenCentral()
    maven(url = uri("https://jitpack.io"))
  }
}
rootProject.name = "CanvasTerminalAndroid"
include(":app")
include(":third_party:emulatorview")
include(":third_party:term")
include(":third_party:libtermexec")

// Point libtermexec to vendored original module with JNI build
project(":third_party:libtermexec").projectDir = File(rootDir, "third_party/Android-Terminal-Emulator-master/libtermexec")
