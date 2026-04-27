import tkinter as tk
from tkinter import messagebox  
import socket
import threading
import json
import time
import random
import os

# ==============================
# Player client
# ==============================
class PlayerClient:
    def __init__(self, server_ip, server_port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((server_ip, server_port))

        self.last_msg = []
        self.username = None
        self.player_id = None
        self.selected_portrait = None
        self.portrait_id = None
        self.votes_for = None
        self.portrait_map = {}
        self.eliminated = []
        self.impostor = None
        self.impostor_won = False
        self.active_player = None
        self.unavailable_portraits = []

        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        buffer = ""
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break

                buffer += data.decode()

                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    self.last_msg.append(msg)

            except ConnectionError:
                break

    def send(self, msg):
        msg = json.dumps(msg) + "\n"
        self.socket.send(msg.encode())

# ==============================
# Base view shared by Lobby/Game
# ==============================
class BaseView(tk.Frame):

    def __init__(self, master, client):
        super().__init__(master, bg="#02085c")
        self.client = client

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.portrait_frame = tk.Frame(self, bg="#02085c")
        self.portrait_frame.grid(row=0, column=0, columnspan=2, sticky="n", pady=40)

        self.player_portraits = {}
        self.current_usernames = []
        self.portrait_images = {}

        self.bind("<Configure>", self.on_resize)

    def update_portraits(self, usernames):
        
        if usernames == self.current_usernames:
            return
        
        self.current_usernames = usernames

        for widget in self.portrait_frame.winfo_children():
            widget.destroy()

        self.player_portraits.clear()

        n = min(len(usernames), 8)
        if n == 0:
            return

        # width = max(self.winfo_width(), 900)
        # portrait_size = min(140, int(width / (n * 2.8)))
        # spacing = int(portrait_size * 0.3)
        portrait_size = 140

        base_dir = os.path.dirname(os.path.abspath(__file__))
        sprite_dir = os.path.join(base_dir, "Sprites")

        for i, name in enumerate(usernames[:8]):

            player_frame = tk.Frame(self.portrait_frame, bg="#02085c")
            # player_frame.grid(row=0, column=i, padx=spacing)
            # padx = max(5, self.winfo_width() // 100)
            player_frame.grid(row=0, column=i, sticky="n", padx=10)
            self.portrait_frame.grid_columnconfigure(i, weight=1)

            portrait = tk.Frame(
                player_frame,
                width=portrait_size+35,
                height=portrait_size+15,
                bg="#02085c",
                highlightbackground="white",
                highlightthickness=0
            )

            portrait.pack()
            portrait.pack_propagate(False)
            
            if name in self.client.portrait_map:
                portrait_file = self.client.portrait_map[name]

                path = os.path.join(sprite_dir, portrait_file)

                img = tk.PhotoImage(file=path)  
                # img = img.subsample(
                #     max(1, int(img.width()/portrait_size)),
                #     max(1, int(img.height()/portrait_size))
                # )
                scale = max(img.width() / portrait_size, img.height() / portrait_size)
                scale = max(1, int(scale))

                img = img.subsample(scale, scale)

                label = tk.Label(portrait, image=img, bg="#02085c")
                label.image = img
                label.pack(expand=True)
                label.bind("<Button-1>", lambda e, target=name: self.master.game_view.send_vote(target))

            if name != self.client.active_player:
                name_label = tk.Label(player_frame, text=name, fg="white", bg="#02085c")
                name_label.pack(pady=5)

            self.player_portraits[name] = portrait
            
            # if name in self.client.eliminated:
            #     portrait.config(highlightbackground="red", highlightthickness=5)    

    def on_resize(self, event):
        pass
        # if self.current_usernames:
        #     self.update_portraits(self.current_usernames)

# ==============================
# Start screen
# ==============================

class StartupView(tk.Frame):
        
    def __init__(self, master):
        super().__init__(master, bg="#02085c")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.control_frame = tk.Frame(self, bg="#02085c")
        self.control_frame.grid(row=0, column=0)

        self.label = tk.Label(self.control_frame, text="Enter server IP:", fg="white", bg="#02085c")
        self.label.pack(pady=(0, 10))

        self.entry = tk.Entry(self.control_frame)
        self.entry.insert(0, "192.168.1.2")   # default value
        self.entry.pack(pady=5)
        self.entry.bind("<Return>", lambda event: self.enter_IP())

        self.join_btn = tk.Button(self.control_frame, text="Start game", command=self.enter_IP)
        self.join_btn.pack(pady=5)

    def enter_IP(self):

        self.master.server_ip = self.entry.get().strip()
        if self.master.server_ip:
          self.master.enter_game()

class StartView(tk.Frame):

    def __init__(self, master, client):
        super().__init__(master, bg="#02085c")
        self.client = client

        self.active_view = False

        self.selected_portraits = None
        self.selected_index = None
        self.portrait_images = []

        # Shared portrait identifiers
        self.sprite_files = [
            "Monkey guy 1.png",
            "Cod guy 3.png",
            "Cat guy 1.png",
            "Crystal guy 1.png",
            "Fox 1.png",
            "Frog king 1.png",
            "Lava guy 1.png",
            "Owl dude 1.png",
            "Plant guy 1.png",
            "Radish guy 1.png",
            "Robo plant 1.png",
            "Slime guy 1.png"
        ]

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Portrait selection ---
        self.portrait_label = tk.Label(self, text="Select your character", fg="white", bg="#02085c", font=("Arial", 16))
        self.portrait_label.grid(row=0, column=0, pady=(0, 0), sticky="nsew")

        self.portrait_frame = tk.Frame(self, bg="#02085c")
        self.portrait_frame.grid(row=1, column=0, pady=(0,0), sticky="nsew")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        sprite_dir = os.path.join(base_dir, "Sprites")

        for i, filename in enumerate(self.sprite_files):
            path = os.path.join(sprite_dir, filename)

            img = tk.PhotoImage(file=path)
            img = img.subsample(2, 2)
            self.portrait_images.append(img)

            btn = tk.Label(self.portrait_frame, image=img, bd=3, relief="flat", bg="#02085c")
            btn.grid(row=i//6, column=i%6, padx=10, pady=10)

            btn.bind("<Button-1>", lambda e, idx=i: self.select_portrait(idx))

        # --- Username entry and button ---
        self.control_frame = tk.Frame(self, bg="#02085c")
        self.control_frame.grid(row=2, column=0, pady=(0,10), sticky="nsew")

        self.label = tk.Label(self.control_frame, text="Enter username:", fg="white", bg="#02085c")
        self.label.pack()

        self.entry = tk.Entry(self.control_frame)
        self.entry.pack(pady=5)
        self.entry.bind("<Return>", lambda event: self.join_game())

        self.join_btn = tk.Button(self.control_frame, text="Enter Lobby", command=self.join_game)
        self.join_btn.pack()

    def select_portrait(self, idx):
        if str(idx) in (self.client.unavailable_portraits or []):
            messagebox.showwarning("Unavailable", "This character is already taken.", parent=self)
            print(self.client.unavailable_portraits)
            return

        self.selected_index = idx
        self.client.selected_portrait = self.portrait_images[idx]
        self.client.portrait_id = self.sprite_files[idx]
        self.client.send(str(idx))

    def join_game(self):
        username = self.entry.get().strip()
        if username and self.selected_index is not None:
            self.client.username = username
            self.client.send(username)
            self.master.show_lobby()

    def poll_server(self):

        if not self.active_view:
            return
        
        while self.client.last_msg:
            try:
                raw_msg = self.client.last_msg.pop(0)
                msg = json.loads(raw_msg)

                if msg.get("type") == "Unavailable portraits":
                    self.client.unavailable_portraits = msg.get("Portraits", [])

            except json.JSONDecodeError:
                pass

        self.after(100, self.poll_server)

# ==============================
# Lobby view
# ==============================
class LobbyView(BaseView):

    def __init__(self, master, client):
        super().__init__(master, client)

        self.active_view = False

        self.control_frame = tk.Frame(self, bg="#02085c")
        self.control_frame.grid(row=1, column=0, sticky="sw", padx=80, pady=80)

        self.ready_btn = tk.Button(self.control_frame, text="Ready to play!", command=self.send_ready)
        self.ready_btn.pack()
        
        self.chat_frame = tk.Frame(self, bg="#02085c", highlightbackground="white", highlightthickness=3)
        self.chat_frame.grid(row=1, column=1, sticky="se", padx=80, pady=10)
        self.chat_frame.grid_propagate(False)
        self.chat_frame.config(width=420, height=320)

        self.chat_box = tk.Text(self.chat_frame, width=40, height=15, bg="white", fg="black")
        self.chat_box.pack(padx=20, pady=(20, 5))

        self.input_frame = tk.Frame(self.chat_frame, bg="#02085c")
        self.input_frame.pack(pady=(0, 20), padx=20, fill="x")

        self.chat_input_entry = tk.Entry(self.input_frame, width=30)
        self.chat_input_entry.pack(side="left", fill="x", expand=True)
        self.chat_input_entry.bind("<Return>", lambda event: self.send_chat())

        self.send_chat_btn = tk.Button(self.input_frame, text="Send chat", command=self.send_chat)
        self.send_chat_btn.pack(side="left", padx=(5,0))

        # self.poll_server()

    def send_ready(self):
        msg = {"text": "ready to play"}
        self.client.send(msg)
        self.ready_btn.config(state="disabled")

    def send_chat(self):
        text = self.chat_input_entry.get().strip()
        if text:
            msg = {"type": "chat", "message": text}
            self.client.send(msg)
            self.chat_input_entry.delete(0, tk.END)
    
    def update_chat(self, message):
        self.chat_box.config(state="normal")
        self.chat_box.delete(1.0, tk.END)

        for username, chat_msg in message.get("chat", {}).items():
            self.chat_box.insert(tk.END, f"{chat_msg}\n")

        self.chat_box.config(state="disabled")

    def poll_server(self):

        if not self.active_view:
            return
        
        while self.client.last_msg:
            try:
                raw_msg = self.client.last_msg.pop(0)
                msg = json.loads(raw_msg)

                if msg.get("type") == "portraits":
                    self.client.portrait_map = msg.get("portraits")

                if msg.get("type") == "Players in the lobby:":
                    self.update_portraits(msg.get("Usernames", []))
                
                if msg.get("type") == "chat_history":
                    self.update_chat(msg)

                if msg.get("type") == "start game":
                    self.master.start_game()
                    return

            except json.JSONDecodeError:
                pass

        self.after(100, self.poll_server)

# ==============================
# Game view
# ==============================
class GameView(BaseView):

    def __init__(self, master, client):
        super().__init__(master, client)

        self.active_view = False

        self.voting_active = False

        self.control_frame = tk.Frame(self, bg="#02085c")
        self.control_frame.grid(row=1, column=0, sticky="sw", padx=50, pady=80)

        self.clue_label = tk.Label(self.control_frame, text="", font=("Arial", 16), fg="white", bg="#02085c",width=40,)
        self.clue_label.pack(pady=10, anchor="center")

        self.input_entry = tk.Entry(self.control_frame)
        self.input_entry.pack(pady=5, anchor="center")
        self.input_entry.config(state="disabled")
        self.input_entry.bind("<Return>", lambda event: self.send_input())

        self.word_or_imp_label = tk.Label(self.control_frame, text="", font=("Arial", 12))
        self.word_or_imp_label.pack(pady=5, anchor="center")

        # self.impostor_label = tk.Label(self.control_frame, text="", font=("Arial", 12), fg="red")
        # self.impostor_label.pack(pady=5)

        self.submit_btn = tk.Button(self.control_frame, text="Submit", command=self.send_input)
        self.submit_btn.config(state="disabled")
        self.submit_btn.pack(pady=10, anchor="center")

        self.category_label = tk.Label(self.control_frame, text="", font=("Arial", 12))
        self.category_label.pack(pady=5, anchor="center")

        self.history_frame = tk.Frame(self, bg="#02085c", highlightbackground="white", highlightthickness=3)
        self.history_frame.grid(row=1, column=1, sticky="sew", padx=80, pady=40)

        self.history_frame.grid_propagate(False)
        self.history_frame.config(width=320, height=320)

        self.timer = tk.Label(self.history_frame, width=15, bg="white", fg="black")
        self.timer.pack(side="bottom", padx=1, pady=1)

        self.skip_vote_btn = tk.Button(self.history_frame, text="Skip vote", command=self.skip_vote)
        self.skip_vote_btn.config(state="disabled")
        self.skip_vote_btn.pack(pady=5, anchor="center")

        self.clue_title = tk.Label(self.history_frame, text="Game clues", font=("Arial", 14, "bold"), bg="#02085c", fg="white")
        self.clue_title.pack(pady=(5, 0))
        self.clue_text = tk.Text(self.history_frame, width=65, height=15, bg="white", fg="black", state="disabled")
        self.clue_text.pack(padx=20, pady=20)
        self.clue_text.tag_configure("red_text", foreground="red")
        self.clue_text.tag_configure("green_text", foreground="green")
        self.clue_text.tag_configure("bold_text", font=("TkDefaultFont", 12, "bold"))

        self.end_btn = tk.Button(self.control_frame, text="End game", command=self.end_game)
        self.end_btn.config(state="active")
        self.end_btn.pack(pady=10, anchor="center")

        # self.poll_server()

    def poll_server(self):

        if not self.active_view:
            return
        
        while self.client.last_msg:
            try:
                raw_msg = self.client.last_msg.pop(0)
                msg = json.loads(raw_msg)

                if msg.get("type") == "portraits":
                    self.client.portrait_map = msg.get("portraits")

                if msg.get("text") == "You are the impostor!":
                    self.word_or_imp_label.config(text="You are the impostor!", fg="red")

                if msg.get("text") == "Vote for the player you think is the impostor":
                    last_active = self.client.active_player
                    last_active_pf = self.player_portraits[last_active]
                    last_active_pf.config(highlightbackground="white", highlightthickness=0)
                    self.client.active_player = None
                    self.voting_active = True
                    self.skip_vote_btn.config(state="active")
                    self.clue_label.config(text=msg["text"])

                if msg.get("type") == "Players in the game:":
                    self.update_portraits(msg.get("Usernames", []))

                if msg.get("type") == "Category":
                    self.category_label.config(text=f"Category: {msg.get('Category', '')}")

                if msg.get("type") == "Word":
                    self.word_or_imp_label.config(text=f"Your word: {msg.get('Word', '')}")

                if msg.get("type") == "clue_history":   
                    self.clue_text.config(state="normal")
                    #self.clue_text.delete(1.0, tk.END)
                    if msg.get("clues") != "game over":
                        for username, clues in msg.get("clues", {}).items():
                            self.clue_text.insert(tk.END, f"{username}: {', '.join(clues)}\n")
                        self.clue_text.config(state="disabled")

                if msg.get("type") == "active_player":
                    if self.client.active_player:
                        last_active = self.client.active_player
                        last_active_pf = self.player_portraits[last_active]
                        last_active_pf.config(highlightbackground="white", highlightthickness=0)
                    self.client.active_player = msg.get("active")
                    if self.client.active_player in self.player_portraits:
                        portrait_frame = self.player_portraits[self.client.active_player]
                        portrait_frame.config(highlightbackground="lawn green", highlightthickness=5)

                if msg.get("text") == "Write a word to give as a clue":
                    self.clue_label.config(text=msg["text"])
                    self.submit_btn.config(state="active")
                    self.input_entry.config(state="normal")
                
                if msg.get("type") == "voting results":
                    if msg.get("result") == "vote skipped":
                        self.clue_text.config(state="normal")
                        self.clue_text.insert(tk.END, "Voting skipped. The game goes on....\n", ("green_text", "bold_text"))
                        self.clue_text.config(state="disabled")

                    elif msg.get("result") == "vote tied":
                        self.clue_text.config(state="normal")
                        self.clue_text.insert(tk.END, "No player was voted out. The game goes on....\n", ("green_text", "bold_text"))
                        self.clue_text.config(state="disabled")

                    elif msg.get("result") == "A player has been eliminated":
                        for elim in msg.get("eliminated players", ''):
                            if elim not in self.client.eliminated :

                                self.clue_text.config(state="normal")
                                self.clue_text.insert(tk.END, f"{elim} has been voted out. They were not the impostor.\n", ("red_text", "bold_text"))
                                self.clue_text.config(state="disabled")

                                self.client.eliminated.append(elim)
                                portrait_frame = self.player_portraits[elim]
                                portrait_frame.config(highlightbackground="red", highlightthickness=5)

                    self.skip_vote_btn.config(state="disabled")

                # if msg.get("type") == "skip":
                #     self.clue_text.config(state="normal")
                #     self.clue_text.insert(tk.END, "Voting skipped. The game goes on....\n", ("green_text", "bold_text"))
                #     self.clue_text.config(state="disabled")
                
                # if msg.get("type") == "tie vote":
                #     self.clue_text.config(state="normal")
                #     self.clue_text.insert(tk.END, "No player was voted out. The game goes on....\n", ("green_text", "bold_text"))
                #     self.clue_text.config(state="disabled")
        
                if msg.get("text") == "Impostor lost":
                    self.client.impostor_won = False
                
                if msg.get("text") == "Impostor won":
                    self.client.impostor_won = True

                if msg.get("type") == "Reveal impostor":
                    self.client.impostor = msg.get("impostor", "")
                    self.master.game_over()
                    return
                
                if msg.get("time") is not None:
                    self.timer.config(text=str(int(msg["time"])))
                    

            except json.JSONDecodeError:
                pass
        
        self.after(100, self.poll_server)

    def send_input(self):
        text = self.input_entry.get().strip()
        msg = {"text": text}
        if text:
            self.client.send(msg)
            self.input_entry.delete(0, tk.END)
            self.submit_btn.config(state="disabled")
            self.input_entry.config(state="disabled")
    
    def skip_vote(self):
        msg = {"vote": "skip"}
        self.client.send(msg)
        self.voting_active = False
        self.skip_vote_btn.config(state="disabled")
    
    def portrait_info(self):

        user_portrait = self.client.portrait_id

        msg = {
            "type": "user_portrait",
            "portrait": user_portrait
        }
        self.client.send(msg)

    def select_vote(self, idx):
        self.selected_index = idx
        self.client.selected_portrait = self.portrait_images[idx]

    def send_vote(self, target):

        if not self.voting_active:
            return
        
        if target in self.client.eliminated:
            return

        msg = {"vote": target}
        self.client.send(msg)
        self.voting_active = False

    def end_game(self):
        reset_msg = {
            "text": "game over"
        }   
        self.client.send(reset_msg)

    
class GameOverView(BaseView):

    def __init__(self, master, client):
        super().__init__(master, client)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.control_frame = tk.Frame(self, bg="#02085c")
        self.control_frame.grid(row=0, column=0)

        # Text above portrait
        if self.client.impostor_won:
            self.top_text = tk.Label(self.control_frame, text="The impostor won!", fg="red", bg="#02085c", font=("Arial", 16))
            self.top_text.pack(pady=(0, 20))
        
        else:
            self.top_text = tk.Label(self.control_frame, text="The impostor lost!", fg="lawn green", bg="#02085c", font=("Arial", 16))
            self.top_text.pack(pady=(0, 20))

        # Button
        self.continue_btn = tk.Button(self.control_frame, text="Back to lobby", command=self.to_lobby)
        self.continue_btn.pack(pady=10)

    def show_impostor(self):
        # Remove previous widgets created by this function
        if hasattr(self, "portrait_frame"):
            self.portrait_frame.destroy()

        if hasattr(self, "bottom_text"):
            self.bottom_text.destroy()

        impostor = self.client.impostor

        # Portrait frame
        self.portrait_frame = tk.Frame(
            self.control_frame,
            width=180,
            height=180,
            bg="#02085c",
            highlightbackground="white",
            highlightthickness=3
        )
        self.portrait_frame.pack()
        self.portrait_frame.pack_propagate(False)

        if impostor in self.client.portrait_map:
            portrait_file = self.client.portrait_map[impostor]

            base_dir = os.path.dirname(os.path.abspath(__file__))
            sprite_dir = os.path.join(base_dir, "Sprites")
            path = os.path.join(sprite_dir, portrait_file)

            img = tk.PhotoImage(file=path)
            img = img.subsample(2, 2)

            label = tk.Label(self.portrait_frame, image=img, bg="#02085c")
            label.image = img
            label.pack(expand=True)
            
        # Text below portrait
        self.bottom_text = tk.Label(self.control_frame, text=f"The impostor was {impostor}!", fg="white", bg="#02085c", font=("Arial", 14))
        self.bottom_text.pack(pady=(20, 10))

    def to_lobby(self):
        lobby_msg = {
            "type": "back to lobby"
        }   
        self.client.send(lobby_msg)

        self.client.eliminated = []
        self.client.impostor = None
        self.client.impostor_won = False
        self.client.active_player = None

        self.master.back_to_lobby()

# ==============================
# Main Application
# ==============================

class App(tk.Tk):
 
    def __init__(self, server_ip="127.0.0.1", server_port=1234):

        super().__init__()
        self.title("Word Impostor")
        self.geometry("900x600")
        self.local_ip = server_ip
        self.server_ip = None
        self.server_port = server_port

        self.startup = StartupView(self)
        self.startup.pack(fill="both", expand=True)


    def enter_game(self):
        ip_to_use = self.server_ip
        if self.server_ip == "192.168.":  # default entry not changed
            ip_to_use = self.local_ip   # keep default argument
        
        self.client = PlayerClient(ip_to_use, self.server_port)

        self.start_view = StartView(self, self.client)
        self.lobby_view = LobbyView(self, self.client)
        self.game_view = GameView(self, self.client)
        # self.game_over_view = GameOverView(self, self.client)

        self.startup.pack_forget()
        self.start_view.active_view = True
        self.start_view.pack(fill="both", expand=True)
        self.start_view.poll_server()

    def show_lobby(self):
        self.game_view.portrait_info()
        self.start_view.active_view = False
        self.start_view.pack_forget()
        self.lobby_view.active_view = True
        self.lobby_view.pack(fill="both", expand=True)
        self.lobby_view.poll_server()
        
    def start_game(self):
        self.lobby_view.active_view = False
        self.lobby_view.pack_forget()
        self.game_view.active_view = True
        self.game_view.pack(fill="both", expand=True)
        self.game_view.poll_server()
    
    def game_over(self):
        self.game_view.current_usernames = []

        self.game_view.clue_text.config(state="normal")
        self.game_view.clue_text.delete("1.0", "end")
        self.game_view.clue_text.config(state="disabled")
        self.game_view.active_view = False
        self.game_view.pack_forget()
        self.game_over_view = GameOverView(self, self.client)
        self.game_over_view.pack(fill="both", expand=True)
        self.game_over_view.show_impostor()

    def back_to_lobby(self):
        self.game_over_view.pack_forget()
        self.lobby_view.active_view = True
        self.lobby_view.pack(fill="both", expand=True)
        self.lobby_view.poll_server()
        self.lobby_view.ready_btn.config(state="active")

# ==============================
# Run
# ==============================
if __name__ == "__main__":
    app = App()
    app.mainloop()
