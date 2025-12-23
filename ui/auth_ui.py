
import gradio as gr
from auth_service import register_user, login_user

def auth_screen(user_state: gr.State):
    gr.Markdown("##  Login / Register")

    with gr.Row():
        # ---------- LOGIN ----------
        with gr.Column():
            gr.Markdown("### Login")
            login_username = gr.Textbox(label="Username")
            login_password = gr.Textbox(label="Password", type="password")
            login_btn = gr.Button("Login", variant="primary")
            login_msg = gr.Markdown()

        # ---------- REGISTER ----------
        with gr.Column():
            gr.Markdown("### Register")
            reg_username = gr.Textbox(label="Username (no spaces)")
            reg_display = gr.Textbox(label="Display name")
            reg_email = gr.Textbox(label="Email")
            reg_password = gr.Textbox(label="Password (min 6)", type="password")
            reg_btn = gr.Button("Create account")
            reg_msg = gr.Markdown()

    gr.Markdown("---")
    current_user = gr.Markdown("Not logged in.")

    # ---------- handlers ----------
    def do_login(u, p):
        ok, res = login_user(u, p)
        if ok:
            # res is user_data dict (from Firestore)
            username = res.get("username", u)
            # Success: clear login fields
            return username, f"✅ Logged in as (`{username}`)", f"✅ Welcome back!", "", ""
        # Error: keep fields for retry
        return None, "Not logged in.", f"❌ {res}", gr.update(), gr.update()

    def do_register(u, d, pw, em):
        ok, msg = register_user(u, d, pw, em)
        if ok:
            # Success: clear all registration fields
            return f"✅ {msg}", "", "", "", ""
        # Error: keep fields for retry
        return f"❌ {msg}", gr.update(), gr.update(), gr.update(), gr.update()

    login_event = login_btn.click(
        fn=do_login,
        inputs=[login_username, login_password],
        outputs=[user_state, current_user, login_msg, login_username, login_password],
    )

    reg_btn.click(
        fn=do_register,
        inputs=[reg_username, reg_display, reg_password, reg_email],
        outputs=[reg_msg, reg_username, reg_display, reg_password, reg_email],
    )

    return login_event

