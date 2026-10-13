"""CI check: build every installer page in a virtual display and make sure nothing crashes."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import thmi_installer as t
a = t.App()
for page in (a.page_device, a.page_pi, a.page_apps, a.page_write, a.page_thmi, a.page_manage):
    page(); a.update()
a.destroy()
print("GUI OK")
