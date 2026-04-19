import codecs

def version_str():
    return "0.8b"

def manr_app_name():
    return "manr_chat"

def manr_email_address():
    codec = "rot_13"
    em = codecs.encode("znae-pung", codec)
    host = codecs.encode("cebgba.zr", codec)
    return em + "@" + f"{host}"

def manr_user_agent() -> str:
    ua = f"{manr_app_name()}/{version_str()} ({manr_email_address()})"
    return ua