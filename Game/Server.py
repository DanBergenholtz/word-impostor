import random
import socket
import threading
import json
import time
import os
import numpy as np

class Player():

    def __init__(self, connection, username):
        self.socket = connection 
        self.username = username
        self.player_id = None #player_id will be equal to their index in the game.players list
        self.impostor = False
        self.eliminated = False
        self.last_msg = None
        
    def send(self, msg):
        msg = json.dumps(msg)
        self.socket.send((msg + "\n").encode())

    def receive(self):
        return self.socket.recv(1024).decode()
    
class Game():

    def __init__(self, turn_time):

        self.players = [] #List of player objects, created in the lobby
        self.players_in_lobby = []
        self.eliminated_players = []
        self.impostor_in_game = True
        self.two_impostors = False
        self.word_category = None
        self.secret_word = None
        self.impostor = None
        self.second_impostor = None
        self.clue_history = {}
        self.turn_timer = turn_time
        self.chat_history = {}
        self.portraits = {}
        self.keep_playing = True
        self.selected_portraits = []

    def start_game(self, words, prob = 0.99):

        #set up game
        if random.random() <= prob:
            imps = np.random.choice(self.players, size=2, replace=False)
            self.impostor = imps[0]
            self.second_impostor = imps[1]
            self.two_impostors = True
        else:
            self.impostor = random.choice(self.players)
        
        self.word_category = random.choice(list(words.keys())) # Pick a random category
        self.secret_word = random.choice(words[self.word_category]) # Pick a random word from that category

        self.keep_playing = True


    def starting_info(self):

        players_msg = {
            "type": "Players in the game:",
            "Usernames": [p.username for p in self.players]
        }

        portraits_msg = {
            "type": "portraits",
            "portraits": self.portraits
        }

        category_msg = {
            "type": "Category",
            "Category": self.word_category
        }

        word_msg = {
            "type": "Word",
            "Word": self.secret_word
        }

        imp_msg = {
            "text": "You are the impostor!"
        }

        two_imp_msg = {
            "type": "two impostors in the game"
        }

        for player in self.players:
            player.send(portraits_msg)
            player.send(players_msg)
            player.send(category_msg)

            if self.two_impostors:
                player.send(two_imp_msg)
                if player is not self.impostor and player is not self.second_impostor:
                    player.send(word_msg)
                else:
                    player.send(imp_msg)
            
            else:
                if player is not self.impostor:
                    player.send(word_msg)
                else:
                    player.send(imp_msg)

    def reset_to_lobby(self):
        global server_state

        if not self.two_impostors:
            impostor_msg = {
                "type": "Reveal impostor",
                "impostor": self.impostor.username
            }
            print(f"The impostor was {self.impostor.username}")

            if not self.impostor_in_game: #Impostor was voted out
                won_lost_msg = {
                    "text": "Impostor lost"
                }
            else: #Impostor won
                won_lost_msg = {
                    "text": "Impostor won"
                }

        else:  #Two impostors
            impostor_msg = {
                "type": "Reveal impostors",
                "impostor 1": self.impostor.username,
                "impostor 2": self.second_impostor.username
            }
            print(f"The impostors were {self.impostor.username} and {self.second_impostor.username}")

            if not self.impostor_in_game: #Impostor was voted out
                won_lost_msg = {
                    "text": "Impostors lost"
                }
            else: #Impostor won
                won_lost_msg = {
                    "text": "Impostors won"
                }
        for player in self.players:
            player.send(won_lost_msg)
            player.send(impostor_msg)
            player.last_msg = None
            
        #resets game state
        self.players_in_lobby = []
        self.eliminated_players = []
        self.clue_history = {}
        self.chat_history = {}
        self.impostor_in_game = True
        self.two_impostors = False
        self.impostor = None
        self.second_impostor = None
        self.word_category = None
        self.secret_word = None

        server_state = "lobby"
        print("Game reset and server_state = lobby.")

            
    def give_clue(self, player, game):

        clue_msg = {
            "text" : "Write a word to give as a clue",
            
        }
        player.send(clue_msg)
        print(f"Clue message sent to {player.username}")
        timer = self.turn_timer*10
        while player.last_msg is None:
            if timer % 10 == 0:
                time_msg = {
                    "time" : timer // 10
                }
                for p in game.players:
                    p.send(time_msg)
            timer -= 1
            time.sleep(0.1)

        if player.last_msg == "game over":
            player.last_msg = None
            return "game over"
        
        print(f"Player {player.username} gave clue : {player.last_msg}")
        clue = player.last_msg["text"]
        player.last_msg = None

        return clue

    def active_player(self, username):
        active_msg = {
            "type": "active_player",
            "active" : username
        }
        for player in self.players:
            player.send(active_msg)

    def vote(self):

        vote_msg = {
            "text" : "Vote for the player you think is the impostor",
        }
    
        votes = {}
    
        for p in self.players:
            if p.username not in self.eliminated_players:
                p.send(vote_msg)
                print(f"Vote message sent to {p.username}")

        while len(votes) < len(self.players) - len(self.eliminated_players):
            for p in self.players:
                if p.last_msg is not None: 
                    if p.last_msg == "game over":
                        return "game over"
                    else:
                        votes[p.username] = p.last_msg.get("vote") #will be a username or skip
                        p.last_msg = None
                        print(f"Vote received from {p.username}")

            time.sleep(0.01)
        
        print("All votes received")

        vote_count = {}

        for username in votes.values():
            if username not in vote_count:
                vote_count[username] = 0
            vote_count[username] += 1

        if vote_count.get('skip', 0) * 2 >= len(self.players) - len(self.eliminated_players):
            return "skip"

        tie_checker = sorted([count for count in vote_count.values()]) #list of all counts sorted
        if len(tie_checker) > 1 and tie_checker[-1] == tie_checker[-2]:
            return None
        else:
            return max(vote_count, key=vote_count.get) #username with most votes
        
    def voted_out_message(self, flag="default"):

        if flag == "vote skipped":
            msg = {
                "type" : "voting results",
                "result" : "vote skipped"
            }
        
        elif flag == "vote tied":
            msg = {
                "type" : "voting results",
                "result" : "vote tied"
            }
        
        elif flag == "two impostors":
            msg = {
                "type": "voting results",
                "result": "An impostor has been eliminated",
                "eliminated players": self.eliminated_players
            }

        else: 
            msg = {
                "type": "voting results",
                "result": "A player has been eliminated",
                "eliminated players": self.eliminated_players
            }

        for player in self.players:
            player.send(msg)

    def skip_msg(self):

        skip_msg = {
            "type": "skip"
        }

        for player in self.players:
            player.send(skip_msg)

    def tie_vote_msg(self):

        tie_msg = {
            "type": "tie vote"
        }

        for player in self.players:
            player.send(tie_msg)

    def send_clue_history(self):
        # Convert player objects to usernames
        history_dict = {}
        for player, clues in self.clue_history.items() :
            history_dict[player.username] = clues

        # Build the message
        msg = {
            "type": "clue_history",
            "clues": history_dict
        }

        return msg

def handle_player(player, game):
    conn = player.socket
    while True:
        try:
            data = conn.recv(1024)
            if not data:
                break
            message = json.loads(data.decode())

            if message.get("type") == "chat":
                new_msg = f"{player.username}: {message.get('message')}"
                if player.username in game.chat_history:
                    game.chat_history[player.username] += "\n" + new_msg
                else:
                    game.chat_history[player.username] = new_msg

            elif message.get("type") == "user_portrait":
                if player.username in game.portraits:
                    pass
                else:
                    game.portraits[player.username] = message.get("portrait")
            
            elif message.get("text") == "game over":
                game.keep_playing = False
                player.last_msg = message.get("text")
                # player.last_msg = None
            
            elif message.get("type") == "back to lobby":
                game.players_in_lobby.append(player.username)

            else:
                player.last_msg = message

        except ConnectionError:
            break

    print(f"Player {player.username} disconnected.")
    game.players.remove(player)
    game.players_in_lobby.remove(player.username)
    del game.portraits[player.username]
    print(f"Player {player.username} removed.")
    conn.close()

def broadcast_lobby(game):

    global server_state
    # while server_state == "lobby":   
    while True:
        if server_state != "lobby":
            time.sleep(0.1)
            continue
        
        r_t_p = 0

        usernames_msg = {
            "type": "Players in the lobby:",
            "Usernames": game.players_in_lobby
        }

        chat_hist_msg = {
            "type": "chat_history",
            "chat": game.chat_history
        }

        portraits_msg = {
            "type": "portraits",
            "portraits": game.portraits
        }

        lst = [p for p in game.players if not p.last_msg]

        for p in game.players:
            # print(p.username)
            try:
                p.send(portraits_msg)
                p.send(usernames_msg)
                p.send(chat_hist_msg)
            except ConnectionError:
                pass
            if p.last_msg:
                if p.last_msg.get("text") == "ready to play":
                    r_t_p += 1
                    # print("ready to play received")
        
        r_t_p_msg = {
            "type": "start game"
        }

        if r_t_p == len(game.players) and len(game.players) > 0:
            server_state = "in_game"
            print("Server now in game")
            for p in game.players:
                try:
                    p.send(r_t_p_msg)
                    print(f"start message sent to {p.username}")
                except ConnectionError:
                    pass
                p.last_msg = None

        time.sleep(0.1)
    

#%% Game logic
server_state = "lobby"

if __name__ == "__main__":

    game = Game(60)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 1234))
    server.listen(8)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    words_file = os.path.join(BASE_DIR, "words.json")

    with open(words_file) as f:
        words = json.load(f)

    threading.Thread(target=broadcast_lobby, args=(game,), daemon=True).start()
    server.settimeout(0.01)

    while True:

        if server_state == "lobby":
            try: 
                conn, addr = server.accept()
                print("Connection accepted.")
                portraits_msg = {
                    "type": "Unavailable portraits",
                    "Portraits": game.selected_portraits
                }
                conn.send((json.dumps(portraits_msg) + "\n").encode())

                
                message = json.loads(conn.recv(1024).decode())
                while message in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"):
                    selected_portrait_idx = message
                    message = json.loads(conn.recv(1024).decode())
                # username = json.loads(conn.recv(1024).decode())
                username = message
                game.selected_portraits.append(selected_portrait_idx)

                player = Player(conn, username=username)
                game.players.append(player)
                game.players_in_lobby.append(username)

                player.player_id = len(game.players) - 1

                thread = threading.Thread(
                    target=handle_player,
                    args=(player, game),
                    daemon=True
                )
                thread.start()
                print(f"Player {username} has connected.")

            except socket.timeout:
                pass

        elif server_state == "in_game":

            game.start_game(words)
            game.starting_info()
            clue_hist = game.send_clue_history()
            for player in game.players: 
                player.send(clue_hist)
            
            while game.impostor_in_game:

                round_order = [p for p in game.players if p.username not in game.eliminated_players]
                random.shuffle(round_order)

                for current_player in round_order:
                    if game.keep_playing:

                        game.active_player(current_player.username)
                        clue = game.give_clue(current_player, game)

                        if clue == "game over":
                            break

                        game.clue_history[current_player] = [clue]
                        clue_hist = game.send_clue_history()
                        game.clue_history.clear()

                        for player in game.players: 
                            player.send(clue_hist)

                if not game.keep_playing:
                    break

                voted_out = game.vote() #username of player who is voted out, or None if tie, or "skip" if vote skip
                if voted_out == "game over":
                    break
                print(f"{voted_out} was voted out.")

                if voted_out is not None:
                    if voted_out == "skip":
                        game.voted_out_message(flag="vote skipped")

                    else:
                        game.eliminated_players.append(voted_out)

                        if game.two_impostors:
                            if voted_out == game.impostor.username or voted_out == game.second_impostor.username:
                                game.voted_out_message(flag = "two impostors")
                                game.two_impostors = False

                            else:
                                game.voted_out_message()

                        else:
                            if voted_out == game.impostor.username:
                                game.voted_out_message()
                                game.impostor_in_game = False
                            else:
                                game.voted_out_message()

                else:
                    game.voted_out_message(flag="vote tied")
            
            game.reset_to_lobby()


"""
Bugs: 
End game button works but is still buggy. Got stuck/delayed 
Green square only visible for self. ATTENDED. FIXED
Green square not visible for first player. ATTENDED. FIXED.
Highlights not resetting properly when a new game is started. Bugs if someone except imp voted out. ATTENDED. FIXED
Voted out players can still play.  ATTENDED. FIXED.
Voted out players can still be voted for. ATTENDED.
Voted out players can still vote. ATTENDED. 
MAJOR : clicking portrait in gameview before voting breaks everything. Sends message to server. ATTENDED. FIXED
Clue history format is weird. ATTENDED. FIXED.
Portrait sizes weird when >4 players ATTENDED. FIXED
If a player exits the game -> removed from players list too. A player DCs and things crash, at least in lobby. ATTENDED. FIXED
end game funkade ej som det skulle
Vote text doesnt reset always
Skip vote blir inte disabled efter man har röstat?

Add: 
A screen for when a player is voted out that is not the impostor. ADDED
A screen for when no player is voted out and the game continues. ADDED
Something to show which players are eliminated. ADDED
A function so that no two players can have the same portrait
Functionality so that when a player leaves in the lobby, their portrait is removed ADDED.
End game button - take players back to lobby. ADDED.
Skip vote. ADDED
Make broadcast_lobby more efficient - so it doesnt loop multiple over all players all the time.
Se vem man röstat på, gissa på ordet/visa ordet
Eliminated message till den som blivit eliminerad? Istället för ordet/vote message

"""