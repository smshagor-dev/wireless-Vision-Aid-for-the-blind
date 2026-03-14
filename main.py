try:
    from android_apps.main import WVABApp
except Exception:
    from android_kivy.main import WVABApp


if __name__ == "__main__":
    WVABApp().run()
