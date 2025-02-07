import os
import platform

def get_settings(setting):
    settings = {
        "os.link_style": "symlink" if platform.system() == "Linux" else "junction"
    }
    return settings.get(setting)
    
def create_link(symlink, source):
    link_style = get_settings("os.link_style")
    
    # remove symlink before setting
    if os.path.islink(symlink):
        os.remove(symlink)

    # set the symlink based on operating system spec
    if link_style == "symlink":
        os.symlink(source, symlink)
    elif link_style == "junction":
        os.system(f'mklink /J "{symlink}" "{source}"')  # Windows junction link
    else:
        raise ValueError(f"Unsupported link style: {link_style}")
