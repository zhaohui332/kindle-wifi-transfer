[app]

# (str) Title of your application
title = Kindle传书

# (str) Package name
package.name = kindletransfer

# (str) Package domain (needed for android/ios packaging)
package.domain = org.kindle.transfer

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let everything in)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions
source.include_patterns = main.py,README.md

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
requirements = python3,kivy,plyer

# (str) Custom bootstrap
bootstrap = sdl2

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (list) Permissions for Android
android.permissions = INTERNET,ACCESS_WIFI_STATE,ACCESS_NETWORK_STATE,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# (int) Android API to use
android.api = 33

# (int) Minimum API required
android.minapi = 21

# (int) Android SDK version
android.sdk = 33

# (str) Android NDK version
android.ndk = 25b

# (str) Android architecture
android.arch = arm64-v8a

# (str) Garbage collector options
#android.gc = 1

# (bool) Copy Python instead of symlinking
#android.copy_python = 1

# (str) Android package name for Google Play
#android.private_storage = org.kindle.transfer

# (bool) Enable AndroidX
android.enable_androidx = 1

# (bool) Enable ADB debug mode
android.debug = 0

# (str) Log level for ADB
android.log_level = 2

# (str) Windows to run on start
#android.wakelock = 1

# (str) Presplash background color (CSS hex value)
#android.presplash_color = #FFFFFF

# (list) Android add to manifest
#android.manifest.extra_activities =

# (str) Debug layout
#android.fullscreen = 0

# (str) Java source code for the activity
#android.add_src =


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 1

# (str) Path to build artifact storage
warn_on_root = 1

# (str) Android SDK directory
#android.sdk_path =

# (str) Android NDK directory
#android.ndk_path =

# (str) Android ANT directory
#android.ant_path =

# (str) Python-for-android git branch
#p4a.branch = develop

# (str) Requirements file to use
#requirements =

# (str) Cross-compiling toolchain
#android.toolchain =

# (int) Timeout for downloading dependencies
#download.timeout = 60

# (str) Accepted SDK licenses
#android.accept_sdk_license = True
