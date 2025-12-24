

import gradio as gr
from auth_service import register_user, login_user

def auth_screen(user_state: gr.State):
 
    gr.Markdown("##  Login / Register")

    mode = gr.Radio(
        choices=["Login", "Register"],
        value="Login",
        label="",
        interactive=True,
    )

    # -------- Login UI --------
    with gr.Column(visible=True) as login_col:
        login_username = gr.Textbox(label="Username")
        login_password = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login", variant="primary")
        login_msg = gr.Markdown()

    # -------- Register UI --------
    with gr.Column(visible=False) as reg_col:
        reg_username = gr.Textbox(label="Username (no spaces)")
        reg_display = gr.Textbox(label="Display name")
        reg_email = gr.Textbox(label="Email")
        reg_password = gr.Textbox(label="Password (min 6)", type="password")
        reg_btn = gr.Button("Create account")
        reg_msg = gr.Markdown()

    gr.Markdown("---")
    current_user = gr.Markdown("Not logged in.")

    # -------- Switching handler --------
    def switch(m):
        return gr.update(visible=(m == "Login")), gr.update(visible=(m == "Register"))
    
    mode.change(fn=switch, inputs=[mode], outputs=[login_col, reg_col])

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
            
            return (
                f"✅ {msg}<br>Now please login.",
                "", "", "", "",                 # clear register fields
                gr.update(value="Login"),       # switch mode to Login
                gr.update(visible=True),        # show login col
                gr.update(visible=False),       # hide register col
                (u or ""),                      # prefill login username
                ""                              # clear login password
            )
        return (
            f"❌ {msg}",
            gr.update(), gr.update(), gr.update(), gr.update(),
            gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        )

    # Login event is returned to home_ui.py
    login_event = login_btn.click(
        fn=do_login,
        inputs=[login_username, login_password],
        outputs=[user_state, current_user, login_msg, login_username, login_password],
    )
    # Register event updates tab selection + prefill login username
    reg_btn.click(
        fn=do_register,
        inputs=[reg_username, reg_display, reg_password, reg_email],
        outputs=[
            reg_msg,
            reg_username, reg_display, reg_password, reg_email,
            mode,
            login_col, reg_col,
            login_username, login_password
        ],
    )

    return login_event, current_user, login_msg, reg_msg


