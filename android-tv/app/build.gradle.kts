plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "tv.outofstep.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "tv.outofstep.app"
        minSdk = 22          // Fire TV Stick (Fire OS 5) and every Android TV / Google TV since 2015
        targetSdk = 34
        versionCode = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
        versionName = "1.0." + (System.getenv("GITHUB_RUN_NUMBER") ?: "0")
    }

    signingConfigs {
        // Shared test key so new builds install over old ones. Store releases will use a private key.
        getByName("debug") {
            storeFile = rootProject.file("test-signing.keystore")
            storePassword = "outofstep"
            keyAlias = "outofstep"
            keyPassword = "outofstep"
        }
    }

    buildTypes {
        getByName("debug") { signingConfig = signingConfigs.getByName("debug") }
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
