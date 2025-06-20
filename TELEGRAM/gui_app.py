import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import asyncio
import logging
from account_manager import AccountManager
from group_connector import GroupConnector
from database_manager import DatabaseManager
from typing import Optional, Dict, Any
import queue
import threading
from datetime import datetime

class TelegramManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Group Manager")
        self.root.geometry("800x600")
        
        # Initialize managers
        self.account_manager = AccountManager()
        self.db_manager = DatabaseManager()
        self.current_client = None
        self.message_queue = queue.Queue()
        
        # Create GUI elements
        self.create_gui()
        
        # Start message processing
        self.process_messages()
        
    def create_gui(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.login_tab = ttk.Frame(self.notebook)
        self.groups_tab = ttk.Frame(self.notebook)
        self.messages_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.login_tab, text='Login')
        self.notebook.add(self.groups_tab, text='Groups')
        self.notebook.add(self.messages_tab, text='Messages')
        
        # Setup each tab
        self.setup_login_tab()
        self.setup_groups_tab()
        self.setup_messages_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set("Ready")
        
    def setup_login_tab(self):
        # Login frame
        login_frame = ttk.LabelFrame(self.login_tab, text="Account Login", padding=10)
        login_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Phone number entry
        ttk.Label(login_frame, text="Phone Number:").grid(row=0, column=0, pady=5)
        self.phone_var = tk.StringVar()
        self.phone_entry = ttk.Entry(login_frame, textvariable=self.phone_var)
        self.phone_entry.grid(row=0, column=1, pady=5)
        
        # Session name entry
        ttk.Label(login_frame, text="Session Name:").grid(row=1, column=0, pady=5)
        self.session_var = tk.StringVar()
        self.session_entry = ttk.Entry(login_frame, textvariable=self.session_var)
        self.session_entry.grid(row=1, column=1, pady=5)
        
        # Login button
        self.login_button = ttk.Button(login_frame, text="Login", command=self.handle_login)
        self.login_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Verification code frame
        self.verify_frame = ttk.LabelFrame(login_frame, text="Verification", padding=10)
        self.verify_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky='ew')
        self.verify_frame.grid_remove()  # Hidden by default
        
        # Code entry
        ttk.Label(self.verify_frame, text="Enter Code:").grid(row=0, column=0, pady=5)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(self.verify_frame, textvariable=self.code_var)
        self.code_entry.grid(row=0, column=1, pady=5)
        
        # Verify button
        self.verify_button = ttk.Button(self.verify_frame, text="Verify", command=self.handle_verification)
        self.verify_button.grid(row=1, column=0, columnspan=2, pady=5)
        
        # 2FA frame
        self.twofa_frame = ttk.LabelFrame(login_frame, text="Two-Factor Authentication", padding=10)
        self.twofa_frame.grid(row=4, column=0, columnspan=2, pady=5, sticky='ew')
        self.twofa_frame.grid_remove()  # Hidden by default
        
        # Password entry
        ttk.Label(self.twofa_frame, text="2FA Password:").grid(row=0, column=0, pady=5)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.twofa_frame, textvariable=self.password_var, show='*')
        self.password_entry.grid(row=0, column=1, pady=5)
        
        # Submit button
        self.submit_2fa_button = ttk.Button(self.twofa_frame, text="Submit", command=self.handle_2fa)
        self.submit_2fa_button.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Active sessions frame
        sessions_frame = ttk.LabelFrame(self.login_tab, text="Active Sessions", padding=10)
        sessions_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Sessions listbox
        self.sessions_listbox = tk.Listbox(sessions_frame, height=5)
        self.sessions_listbox.pack(fill='both', expand=True)
        
    def setup_groups_tab(self):
        # Group actions frame
        group_frame = ttk.LabelFrame(self.groups_tab, text="Group Actions", padding=10)
        group_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Group link entry
        ttk.Label(group_frame, text="Group Link:").grid(row=0, column=0, pady=5)
        self.group_link_var = tk.StringVar()
        self.group_link_entry = ttk.Entry(group_frame, textvariable=self.group_link_var, width=50)
        self.group_link_entry.grid(row=0, column=1, pady=5)
        
        # Join button
        self.join_button = ttk.Button(group_frame, text="Join Group", command=self.handle_join_group)
        self.join_button.grid(row=0, column=2, padx=5)
        
        # Groups list
        ttk.Label(group_frame, text="Joined Groups:").grid(row=1, column=0, columnspan=3, pady=5)
        self.groups_tree = ttk.Treeview(group_frame, columns=('Name', 'Members', 'Last Updated'))
        self.groups_tree.heading('Name', text='Group Name')
        self.groups_tree.heading('Members', text='Members')
        self.groups_tree.heading('Last Updated', text='Last Updated')
        self.groups_tree.grid(row=2, column=0, columnspan=3, sticky='nsew')
        
    def setup_messages_tab(self):
        # Message composition frame
        message_frame = ttk.LabelFrame(self.messages_tab, text="Compose Message", padding=10)
        message_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Message text
        self.message_text = scrolledtext.ScrolledText(message_frame, height=10)
        self.message_text.pack(fill='both', expand=True, pady=5)
        
        # Send button
        self.send_button = ttk.Button(message_frame, text="Send to Selected Groups", command=self.handle_send_message)
        self.send_button.pack(pady=5)
        
        # Message log
        log_frame = ttk.LabelFrame(self.messages_tab, text="Message Log", padding=10)
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.message_log = scrolledtext.ScrolledText(log_frame, height=10)
        self.message_log.pack(fill='both', expand=True)
        
    def handle_login(self):
        phone = self.phone_var.get().strip()
        session = self.session_var.get().strip()
        
        if not phone or not session:
            messagebox.showerror("Error", "Please enter both phone number and session name")
            return
            
        # Disable input fields
        self.phone_entry.config(state='disabled')
        self.session_entry.config(state='disabled')
        self.login_button.config(state='disabled')
        
        self.status_var.set("Sending verification code...")
        self.current_session = session
        threading.Thread(target=self._async_login, args=(phone, session)).start()
        
    async def get_verification_code(self, session_name: str) -> str:
        # This will be called by AccountManager when code is needed
        future = asyncio.Future()
        
        def on_code_entered():
            code = self.code_var.get().strip()
            if code:
                future.set_result(code)
            else:
                future.set_exception(ValueError("No code entered"))
            
            # Hide verification frame
            self.verify_frame.grid_remove()
            self.code_var.set("")
            
        def show_code_entry():
            self.verify_frame.grid()
            self.verify_button.config(command=on_code_entered)
            self.code_entry.focus()
            
        # Show code entry in main thread
        self.root.after(0, show_code_entry)
        return await future
        
    async def get_2fa_password(self) -> str:
        # This will be called by AccountManager when 2FA is needed
        future = asyncio.Future()
        
        def on_password_entered():
            password = self.password_var.get().strip()
            if password:
                future.set_result(password)
            else:
                future.set_exception(ValueError("No password entered"))
            
            # Hide 2FA frame
            self.twofa_frame.grid_remove()
            self.password_var.set("")
            
        def show_password_entry():
            self.twofa_frame.grid()
            self.submit_2fa_button.config(command=on_password_entered)
            self.password_entry.focus()
            
        # Show password entry in main thread
        self.root.after(0, show_password_entry)
        return await future
        
    def _async_login(self, phone: str, session: str):
        async def login():
            try:
                client, error = await self.account_manager.create_client(
                    session,
                    phone=phone,
                    code_callback=self.get_verification_code,
                    password_callback=self.get_2fa_password
                )
                
                if error:
                    self.message_queue.put(("error", error))
                    self.message_queue.put(("enable_login", None))
                    return
                    
                if client:
                    self.current_client = client
                    self.message_queue.put(("status", "Login successful"))
                    self.message_queue.put(("update_sessions", None))
                    
            except Exception as e:
                self.message_queue.put(("error", f"Login failed: {str(e)}"))
                self.message_queue.put(("enable_login", None))
                
        asyncio.run(login())
        
    def handle_join_group(self):
        group_link = self.group_link_var.get()
        if not group_link:
            messagebox.showerror("Error", "Please enter a group link")
            return
            
        self.status_var.set("Joining group...")
        threading.Thread(target=self._async_join_group, args=(group_link,)).start()
        
    def _async_join_group(self, group_link: str):
        async def join():
            try:
                if not self.current_client:
                    raise Exception("No active client")
                    
                connector = GroupConnector(self.current_client)
                success = await connector.join_group(group_link)
                
                if success:
                    self.message_queue.put(("status", "Successfully joined group"))
                    self.message_queue.put(("update_groups", None))
                else:
                    self.message_queue.put(("error", "Failed to join group"))
            except Exception as e:
                self.message_queue.put(("error", f"Error joining group: {str(e)}"))
                
        asyncio.run(join())
        
    def handle_send_message(self):
        message = self.message_text.get("1.0", tk.END).strip()
        if not message:
            messagebox.showerror("Error", "Please enter a message")
            return
            
        selected_items = self.groups_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Please select at least one group")
            return
            
        self.status_var.set("Sending message...")
        threading.Thread(target=self._async_send_message, args=(message, selected_items)).start()
        
    def _async_send_message(self, message: str, group_ids):
        async def send():
            try:
                if not self.current_client:
                    raise Exception("No active client")
                    
                for group_id in group_ids:
                    group_entity = await self.current_client.get_entity(int(group_id))
                    await self.current_client.send_message(group_entity, message)
                    
                self.message_queue.put(("status", f"Message sent to {len(group_ids)} groups"))
                self.message_queue.put(("log_message", f"Sent message to {len(group_ids)} groups at {datetime.now()}"))
            except Exception as e:
                self.message_queue.put(("error", f"Error sending message: {str(e)}"))
                
        asyncio.run(send())
        
    def process_messages(self):
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "enable_login":
                    self.phone_entry.config(state='normal')
                    self.session_entry.config(state='normal')
                    self.login_button.config(state='normal')
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                elif msg_type == "update_sessions":
                    self.update_sessions_list()
                elif msg_type == "update_groups":
                    self.update_groups_list()
                elif msg_type == "log_message":
                    self.message_log.insert(tk.END, f"{data}\n")
                    self.message_log.see(tk.END)
                    
        except queue.Empty:
            pass
            
        self.root.after(100, self.process_messages)
        
    def update_sessions_list(self):
        self.sessions_listbox.delete(0, tk.END)
        for session in self.account_manager.get_active_clients():
            self.sessions_listbox.insert(tk.END, session)
            
    def update_groups_list(self):
        for item in self.groups_tree.get_children():
            self.groups_tree.delete(item)
            
        if self.current_client:
            threading.Thread(target=self._async_update_groups).start()
            
    def _async_update_groups(self):
        async def update():
            try:
                dialogs = await self.current_client.get_dialogs()
                for dialog in dialogs:
                    if dialog.is_group or dialog.is_channel:
                        self.message_queue.put(("add_group", {
                            'id': dialog.id,
                            'name': dialog.name,
                            'members': getattr(dialog.entity, 'participants_count', 'N/A'),
                            'date': dialog.date.strftime("%Y-%m-%d %H:%M")
                        }))
            except Exception as e:
                self.message_queue.put(("error", f"Error updating groups: {str(e)}"))
                
        asyncio.run(update())

def main():
    root = tk.Tk()
    app = TelegramManagerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
