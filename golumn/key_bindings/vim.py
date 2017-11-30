"""
Handles some common normal mode movement bindings.
"""
import wx
import golumn.key_bindings as key_bindings


def on_key_down(target, evt):
    """
    @return True if `evt` was handled, otherwise False
    """
    kc = evt.GetKeyCode()
    if kc == 74:
        wx.PostEvent(target, key_bindings.MoveDown())
    elif kc == 75:
        wx.PostEvent(target, key_bindings.MoveUp())
    elif kc == 72:
        wx.PostEvent(target, key_bindings.MoveLeft())
    elif kc == 76:
        wx.PostEvent(target, key_bindings.MoveRight())
    return False
