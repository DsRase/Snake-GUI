from tkinter import *
from tkinter import ttk
from random import randint
import os
from tkinter.messagebox import showerror
import socket
import threading as th

BLOCK_SIZE = 20 # Глобальная переменная, отвечающая за размер ячейки

WIDTH = 340 # Ширина игрового поля по умолчанию
HEIGHT = 340 # Высота игрового поля по умолчанию

class Server:
    user = None
    def __init__(self, ip="127.0.0.1", port=9090):
        self.ip = ip
        self.port = port
        self.server = socket.socket()
        self.ready = "unready" # проверка готовности хоста
        # self.server.bind((ip, port))
        # self.server.listen(1) # в змейку одновременно максимум играть могут только двое. Хост не учитывается
        # self.lobby = Lobby()

    def waiting_for_connect(self):
        self.server = socket.socket()
        self.server.bind((self.ip, self.port))
        self.server.listen(1)
        try:
            conn, addr = self.server.accept()
            self.user = User(conn, addr)

            root.widgets["ready_button"]["state"] = 'normal'

            root.widgets["player2"] = ttk.Label(master=root, text="Игрок 2 (Подключившийся) | Не готов")
            root.widgets["player2"].pack(pady=15, ipady=10)

            th.Thread(target=self.waiting_message_client, daemon=True).start()
        except:
            print("GG WP со стороны сервера")
            return

            # self.lobby.send_other(user, "connected") # отправить другому пользователю сообщение о подключении

    # получаем сообщение от пользователя. Выполняем эту функцию, если мы хост
    def waiting_message_client(self):
        while True:
            try:
                data = self.user.conn.recv(1024).decode('utf-8')
            except: break
            if data == "ready":
                root.widgets["player2"]["text"] = "Игрок 2 (Подключившийся) | Готов"
                self.user.ready = "ready"
                if self.ready == "ready":
                    start_online_game()
            elif data == "unready":
                root.widgets["player2"]["text"] = "Игрок 2 (Подключившийся) | Не готов"
                self.user.ready = "unready"
            elif data == "leave":
                # print("Вышел второй игрок")
                root.widgets["player2"].pack_forget()
                root.ready_var.set(0)
                root.widgets["ready_button"]["state"] = "disabled"
                self.user.conn.close()
                self.user = None
                self.waiting_for_connect()
                break
            else:
                # print("мы получили координаты от подключившегося")
                root.drawOnlineScore(data.split('|')[-2])
                root.drawOnlineApple(list(map(float, data.split('|')[-1].split(','))))
                snake_player_cords = []
                for cords in data.split('|')[:-2]:
                    snake_player_cords.append(tuple(map(float, cords.split(','))))
                # data = [list(map(float, cords.split(','))) for cords in data.split('|')[0].split()]
                root.drawOnlineSnake(snake_player_cords)

    # получаем сообщение от сервера. Выполняем эту функцию, если мы подключившийся
    def waiting_message_server(self):
        while True:
            try:
                data = self.server.recv(1024).decode('utf-8')
            except Exception as e:
                print("Ошибка с данными от хоста", e)
                break
            if data == "ready":
                root.widgets["player1"]["text"] = "Игрок 1 (Хост) | Готов"
                self.ready = "ready"
                if self.user.ready == "ready":
                    start_online_game()
            elif data == "unready":
                root.widgets["player1"]["text"] = "Игрок 1 (Хост) | Не готов"
                self.ready = "unready"
            elif data == "leave":
                # print("Вышел хост")
                root.main_menu()
                # root.widgets["player1"].pack_forget()
                break
            else:
                # print("мы получили координаты от хоста")
                root.drawOnlineScore(data.split('|')[-2])
                root.drawOnlineApple(list(map(float, data.split('|')[-1].split(','))))
                snake_player_cords = []
                for cords in data.split('|')[:-2]:
                    # print(cords)
                    snake_player_cords.append(tuple(map(float, cords.split(','))))
                # data = [list(map(float, cords.split(','))) for cords in data.split('|')[0].split()]
                root.drawOnlineSnake(snake_player_cords)

    def connect_to_lobby(self):
        # print(self.ip, self.port)
        # print(self.server)
        try:
            self.server.connect((self.ip, self.port))
            self.user = User(self.server, 122351)
            th.Thread(target=self.waiting_message_server, daemon=True).start()
            return True
        except:
            return False

    def start(self):
        pass

class User:
    def __init__(self, conn, addr, snake=None):
        self.conn = conn
        self.addr = addr
        self.snake = snake # список с координатами каждого участка змейки
        self.ready = "unready" # проверка готовности игрока

# Класс сегмент определяет участок тела змеи 10 на 10 (по умолчанию)
class Segment:
    def __init__(self, x, y, canvas, color="blue"):
        # Отдельно записываем координаты сегмента, для удобного его использования
        self.x = x * BLOCK_SIZE
        self.y = y * BLOCK_SIZE
        self.color = color

        # Сразу отрисовываем новый сегмент, обязательно записываем его ID чтобы потом с ним работать
        self.id = canvas.create_rectangle(self.x, self.y, self.x+BLOCK_SIZE, self.y+BLOCK_SIZE, fill=color, tag='segment')

# Класс змейки, в качестве тела змеи выступают объекты класса Segment
class Snake:
    # Возможные направления змейки
    # Значения - кортежи типа (x, y). Значения в кортежах прибавляются
    # К координатам головы змейки (самый первый сегмент в body)
    directions = {
        "w": (0, -1),
        "s": (0, 1),
        "a": (-1, 0),
        "d": (1, 0)
    }
    def __init__(self, segments, canvas, default_direction="w", number=0):
        self.body = segments

        self.score = 0
        self.number = number

        self.canvas = canvas
        self.direction = Snake.directions[default_direction] # По умолчанию змейка двигается вверх

        # Этот параметр отвечает за постоянное перемещение змейки, и он отключается при её смерти
        self.is_alive = None
        self.all_good = False # это параметр, который говорит о том, что игра запущена

        # Нужно для добавления по этим координатам нового сегмента при съедании яблока
        try:
            self.last_seg_coord = (self.body[-1].x, self.body[-1].y)
        except: pass

    # Класс движения змейки, так же именно там проверяется съела ли змейка яблоко и умерла ли она
    def move(self):
        if self.all_good:
            try:
                self.last_seg_coord = (self.body[-1].x, self.body[-1].y)
                # Последний элемент встаёт на место головы, чуть ниже изменим координаты головы
                x1, y1, x2, y2 =  self.canvas.coords(self.body[0].id) # корды головы
                self.canvas.coords(self.body[-1].id, x1, y1, x2, y2) # меняем координаты последнего участка тела на корды головы
                self.body.insert(1, self.body[-1]) # он меняет свое местоположение на картинке, а значит и в списке тоже меняет
                self.body.pop() # удаляем оригинал
            except: return

            # x1, y1, x2, y2 = self.canvas.coords(self.body[0].id) # Получаем координаты головы
            # Изменяем координаты в соответствии с направлением
            x1 //= BLOCK_SIZE
            y1 //= BLOCK_SIZE
            x2 //= BLOCK_SIZE
            y2 //= BLOCK_SIZE
            x1 += self.direction[0]
            y1 += self.direction[1]
            x2 += self.direction[0]
            y2 += self.direction[1]

            # Если змейка входит в стенку, то выходит она из противоположной
            if x1 >= 17:
                x1 = 0
            if x1 <= -1:
              x1 = 16
            if y1 >= 17:
              y1 = 0
            if y1 <= -1:
              y1 = 16

            # Отрисовываем новое расположение змейки
            self.canvas.coords(self.body[0].id,
                          x1*BLOCK_SIZE, y1*BLOCK_SIZE,
                          x1*BLOCK_SIZE+BLOCK_SIZE, y1*BLOCK_SIZE+BLOCK_SIZE)
            # print(x1, y1)
            # print(apple.x, apple.y)
            # print('-'*20)
            # проверка съеденного яблока
            if (x1*BLOCK_SIZE, y1*BLOCK_SIZE) == (apple.x, apple.y):
                self.add_segment()
                apple.eat_apple(self)

            # проверка смерти об себя
            for i in range(1, len(self.body)):
                xx, yy, _, _ = self.canvas.coords(self.body[i].id)
                if (x1*BLOCK_SIZE, y1*BLOCK_SIZE) == (xx, yy):
                    if snake_2:
                        if self is snake_2:
                            root.drawLocalDeath(snake, snake_2)
                            self.death()
                            snake.death()
                        else:
                            root.drawLocalDeath(snake_2, snake)
                            self.death()
                            snake_2.death()
                    else:
                        try:
                            if root.server:
                                root.main_menu()
                        except: pass
                        root.drawSoloDeath()
                        self.death()
            try:
                # проверка смерти об второго игрока
                if snake_2:
                    if self is not snake_2:
                        for i in range(1, len(snake_2.body)):
                            xx, yy, _, _ = self.canvas.coords(snake_2.body[i].id)
                            if (x1*BLOCK_SIZE, y1*BLOCK_SIZE) == (xx, yy):
                                root.drawLocalDeath(snake_2, snake)
                                self.death()
                                snake_2.death()
                    else:
                        for i in range(1, len(snake.body)):
                            xx, yy, _, _ = self.canvas.coords(snake.body[i].id)
                            if (x1 * BLOCK_SIZE, y1 * BLOCK_SIZE) == (xx, yy):
                                root.drawLocalDeath(snake, snake_2)
                                self.death()
                                snake.death()
            except:
                snake.death()
                snake_2.death()
            try:
                if root.server:
                    data = f"" # координаты через запятую участка1 змеи|корды участка2...|счёт второго игрока|координаты яблока второго игрока
                    for seg in self.body:
                        x1, y1, x2, y2 = self.canvas.coords(seg.id)
                        data += f"{x1},{y1},{x2},{y2}|"
                    data += f"{self.score}|"
                    x1, y1, x2, y2 = self.canvas.coords(apple.id)
                    data += f"{x1},{y1},{x2},{y2}"
                    if root.is_server:
                        # print("МЫ ОТПРАВЛЯЕМ КООРДИНАТЫ ПОЛЬЗОВАТЕЛЮ")
                        # print(root.server.user.conn)
                        # root.server.user.conn.send("ready".encode('utf-8'))
                        root.server.user.conn.send(data.encode('utf-8'))
                    else:
                        # print("МЫ ОТПРАВЛЯЕМ КООРДИНАТЫ ХОСТУ")
                        root.server.server.send(data.encode('utf-8'))
            except:
                root.main_menu()

            self.is_alive = self.canvas.after(100, self.move)

    # Змейка умерла - игра окончена
    def death(self):
        # Отключение движения змейки
        try:
            self.canvas.after_cancel(self.is_alive)
        except: pass
        self.is_alive = None
        self.all_good = False
        self.canvas.unbind("<Key-w>")
        self.canvas.unbind("<Key-a>")
        self.canvas.unbind("<Key-s>")
        self.canvas.unbind("<Key-d>")

    # Изменение направления движения змейки
    def change_direction(self, event):
        if not self.all_good:
            if snake_2:
                snake_2.all_good = True
                snake_2.move()
                snake.all_good = True
                snake.move()
            else:
                self.all_good = True
                self.move()
        if event.keysym in self.directions:
            last_direction = get_key(self.directions, self.direction)
            match event.keysym:
                case 'w':
                    if last_direction == "s": return
                case 's':
                    if last_direction == "w": return
                case 'a':
                    if last_direction == "d": return
                case 'd':
                    if last_direction == "a": return

            match event.keysym:
                case 'Up':
                    if last_direction == "Down": return
                case 'Down':
                    if last_direction == "Up": return
                case 'Left':
                    if last_direction == "Right": return
                case 'Right':
                    if last_direction == "Left": return
            self.direction = self.directions[event.keysym]

    def add_segment(self):
        self.body.append(Segment(self.last_seg_coord[0], self.last_seg_coord[1], self.canvas, color=self.body[-1].color))

class Client:
    @staticmethod
    def save_solo_stats(result): # result - snake.score
        try:
            with open(os.path.abspath('stats.txt'), 'r', encoding='utf-8') as f:
                _ = f.readline()
                best_result = f.readline()
                with open(os.path.abspath('stats.txt'), 'w', encoding='utf-8') as f:
                    best_result = result if result > int(best_result) else best_result
                    f.write(f"{result}\n{best_result}")
        except:
            showerror(title="Ошибка статистики!",
                      message="Повреждены файлы статистики. Ваша статистика будет обнулена.")
            with open(os.path.abspath('stats.txt'), 'w') as f:
                f.write('0\n0')

    @staticmethod
    def save_local_stats(winner: Snake, loser: Snake):
        with open(os.path.abspath("local_stats.txt"), 'w', encoding='utf-8') as f:
            f.write(f"Игрок номер {winner.number+1} - {winner.score}\nИгрок номер {loser.number+1} - {loser.score}")

    @staticmethod
    def get_local_stats():
        if not os.path.exists(os.path.abspath("local_stats.txt")):
            Client.save_local_stats(Snake(None, None, number=0), Snake(None, None, number=1))
        with open(os.path.abspath("local_stats.txt"), 'r', encoding='utf-8') as f:
            result_win = f.readline()
            result_lose = f.readline()
        return (result_win, result_lose)

    @staticmethod
    def get_last_solo_result():
        try:
            with open(os.path.abspath('stats.txt'), 'r', encoding='utf-8') as f:
                last_result = f.readline()
            return int(last_result)
        except:
            showerror(title="Ошибка статистики!",
                      message="Повреждены файлы статистики. Ваша статистика будет обнулена.")
            with open(os.path.abspath('stats.txt'), 'w', encoding='utf-8') as f:
                f.write('0\n0')
            return 0

    @staticmethod
    def get_best_solo_result():
        try:
            with open(os.path.abspath('stats.txt'), 'r', encoding='utf-8') as f:
                _ = f.readline()
                best_result = f.readline()
            return int(best_result)
        except:
            showerror(title="Ошибка статистики!",
                      message="Повреждены файлы статистики. Ваша статистика будет обнулена.")
            with open(os.path.abspath('stats.txt'), 'w') as f:
                f.write('0\n0')
            return 0

# Класс яблока, координаты задаются рандомно
class Apple:
    def __init__(self, canvas, x=BLOCK_SIZE*randint(0, WIDTH//BLOCK_SIZE-1), y=BLOCK_SIZE*randint(0, HEIGHT//BLOCK_SIZE-1), color='red'):
        self.x = x
        self.y = y
        self.canvas = canvas
        self.id = canvas.create_oval(x, y, x+BLOCK_SIZE, y+BLOCK_SIZE, fill=color, tag='apple')

    def eat_apple(self, snake, add_score=True):
        if add_score:
            snake.score += 1
            root.drawScore()
        self.x = BLOCK_SIZE*randint(0, WIDTH//BLOCK_SIZE-1)
        self.y = BLOCK_SIZE*randint(0, HEIGHT//BLOCK_SIZE-1)
        # self.check_coords()
        self.canvas.coords(self.id, self.x, self.y, self.x+BLOCK_SIZE, self.y+BLOCK_SIZE)

    # def check_coords(self):
    #     for seg in snake.body:
    #         x1, y1, _, _ = self.canvas.coords(seg.id)
    #         if (self.x, self.y) == (x1//BLOCK_SIZE, y1//BLOCK_SIZE):
    #             self.eat_apple(add_score=False)
    #             break

# Класс игрового поля
class Desk(Tk):
    def __init__(self, width=WIDTH, height=HEIGHT):
        super().__init__()
        # Базовая настройка окна
        self.geometry(f'{width}x{height}+{self.winfo_screenwidth()//2-width//2}+{self.winfo_screenheight()//2-height//2}')
        self.resizable(False, False)
        self.title("Online Snake!")

        self.widgets = dict()

        self.widgets["back_to_menu"] = ttk.Button(text="Назад", command=self.main_menu) # пока не отображаем

        self.widgets["title"] = ttk.Label(text="Онлайн Змейка!", font=('Arial', 15))
        self.widgets["start_solo_game"] = ttk.Button(self, text="Начать одиночную игру", command=start_solo_game)
        self.widgets["start_online_game"] = ttk.Button(self, text="Начать многопользовательскую игру",
                                                       command=self.choose_online_mode)
        self.widgets["show_stat"] = ttk.Button(self, text="Статистика", command=self.show_stat)

        # Объект, на котором будет отрисована вся игра
        self.c = Canvas(self, bg="green", width=width, height=height)
        # Мы должны постоянно держать canvas в фокусе, чтобы без нажатия на окно можно было начать играть

    def main_menu(self, event=None):
        self.restart()
        self.show_main_widgets()

    # выбор между подключением по IP и игрой локально
    def choose_online_mode(self, event=None):
        self.restart()
        self.widgets["ip_connect"] = ttk.Button(text="Подключиться по IP", command=self.ip_connect_show)
        self.widgets["local_connect"] = ttk.Button(text="Играть локально", command=start_local_game)

        self.widgets["ip_connect"].pack(pady=15, ipady=10)
        self.widgets["local_connect"].pack(pady=15, ipady=10)
        self.widgets["back_to_menu"].pack(pady=15, ipady=10)

    # показать поле ввода для подключения по IP
    def ip_connect_show(self):
        self.restart()
        self.widgets["ip_entry"] = ttk.Entry(width=30)
        self.widgets["ip_entry"].pack(pady=15, ipady=10)
        self.widgets["ip_entry"].focus_set()

        self.widgets["connect_by_ip"] = ttk.Button(text="Подключиться по IP", command=lambda: self.lobby(False))
        self.widgets["create_lobby"] = ttk.Button(text="Создать лобби с IP", command=self.lobby)

        self.widgets["connect_by_ip"].pack(pady=15, ipady=10)
        self.widgets["create_lobby"].pack(pady=15, ipady=10)

        self.widgets["error_to_connect"] = ttk.Label(text="Ошибка подключения. Проверьте IP!", font=('Arial', 10))

        self.widgets["back_to_menu"].pack(side=BOTTOM, pady=15, ipady=10)

    # меню лобби. is_server - параметр, который говорит о том, мы запускаем лобби как хост, или мы к нему подключаемся
    def lobby(self, is_server=True): # игрок 1 - хост. игрок 2 - подключившийся
        self.widgets["error_to_connect"].pack_forget()
        self.server = Server(self.widgets["ip_entry"].get())
        self.is_server = is_server
        if not is_server:
            is_connected = self.server.connect_to_lobby()
            if not is_connected:
                self.widgets["error_to_connect"].pack(pady=5, ipady=5)
                return
        else:
            th.Thread(target=self.server.waiting_for_connect, daemon=True).start()

        self.widgets["ip_entry"].pack_forget()
        self.widgets["connect_by_ip"].pack_forget()
        self.widgets["create_lobby"].pack_forget()

        self.widgets["players"] = ttk.Label(text="Игроки в лобби:")
        self.widgets["player1"] = ttk.Label(text="Игрок 1 (Хост) | Не готов")

        self.widgets["players"].pack(pady=15, ipady=10)
        self.widgets["player1"].pack(pady=15, ipady=10)
        self.ready_var = IntVar()
        self.widgets["ready_button"] = ttk.Checkbutton(text="Готов", variable=self.ready_var,
                                                       command=lambda: ready(is_server), state="disabled")
        if not is_server:
            root.widgets["player2"] = ttk.Label(master=root, text="Игрок 2 (Подключившийся) | Не готов")
            root.widgets["player2"].pack(pady=15, ipady=10)
            self.widgets["ready_button"]["state"] = 'normal'

        self.widgets["ready_button"].pack(side=BOTTOM)

    # def disconnect(self, is_server):
    #     if is_server:
    #         self.server.user.conn.send("leave".encode('utf-8'))
    #     else:
    #         self.server.server.send("leave".encode('utf-8'))

    def show_main_widgets(self):
        for key in self.widgets:
            if key in ["players", "player1", "player2", "error_to_connect", "create_lobby", "connect_by_ip", "ip_entry", "back_to_menu", "last_solo_result", "best_solo_result", "ip_connect", "local_connect", "win_local_result", "lose_local_result"]: continue
            self.widgets[key].pack(pady=15, ipady=10)

    def show_stat(self):
        last_solo_result = Client.get_last_solo_result()
        best_solo_result = Client.get_best_solo_result()
        last_winner, last_loser = Client.get_local_stats()
        # тут будет онлайн

        for key in self.widgets:
            self.widgets[key].pack_forget()

        self.widgets["last_solo_result"] = ttk.Label(text=f"Последний результат одиночной игры: {last_solo_result}", font=('Arial', 12))
        self.widgets["win_local_result"] = ttk.Label(text=f"Победитель локальной игры: {last_winner}", font=('Arial', 9))
        self.widgets["lose_local_result"] = ttk.Label(text=f"Проигравший локальной игры: {last_loser}", font=('Arial', 9))
        self.widgets["best_solo_result"] = ttk.Label(text=f"Лучший результат одиночной игры: {best_solo_result}",
                                                     font=('Arial', 12))
        self.widgets["last_solo_result"].pack(pady = 15, ipady= 10)
        self.widgets["best_solo_result"].pack(pady = 15, ipady = 10)

        self.widgets["win_local_result"].pack(pady = 10, ipady= 7)
        self.widgets["lose_local_result"].pack(pady = 10, ipady= 7)

        self.widgets["back_to_menu"].pack(pady = 15, ipady= 10)


    # метод, который очищает всё, что только можно
    def restart(self):
        global snake
        global snake_2
        try:
            self.server.user.conn.send("leave".encode('utf-8'))
            self.server.user.conn.close()
            self.server.user = None
        except: pass
        try:
            self.server.server.send("leave".encode('utf-8'))
            self.server.server.close()
        except: self.server = None
        if snake:
            snake.score = 0
            snake.all_good = False
            snake.is_alive = None
        if snake_2:
            snake_2.score = 0
            snake_2.all_good = False
            snake_2.is_alive = None
        self.c.delete('solo_final_text')
        self.c.delete('segment')
        try:
            self.c.delete('online_score')
            self.c.delete('online_apple')
            self.c.delete('online_snake')
        except: pass
        self.c.delete('apple')
        for key in self.widgets:
            self.widgets[key].pack_forget()
        self.c.pack_forget()

    def drawScore(self):
        try:
            self.c.delete('score')
            self.c.create_text(50, 10, text=f"Счёт: {snake.score}", fill=snake.body[0].color, font="Arial 15", tag='score')
            if snake_2:
                self.c.create_text(WIDTH-80, 10, text=f"Счёт игрока {snake_2.number+1}: {snake_2.score}", fill=snake_2.body[0].color, font="Arial 15",
                                   tag='score')
        except Exception as e: print("GG WP", e)

    def drawSoloDeath(self):
        self.c.delete('score')
        self.c.bind("<Key>", self.main_menu)
        text = f"Вы проиграли! Ваш счёт: {snake.score}"
        if snake.score > Client.get_best_solo_result():
            self.c.create_text(WIDTH // 2, HEIGHT // 2+20, text="И это ваш новый рекорд!", fill='red', font="Arial 15", tag="solo_final_text")

        Client.save_solo_stats(snake.score)
        self.c.create_text(WIDTH//2, HEIGHT//2, text=text, fill='red', font="Arial 15", tag="solo_final_text")
        self.c.create_text(WIDTH//2, HEIGHT//2+50, text=f"Нажмите любую клавишу для продолжения...", fill='red', font="Arial 12", tag="solo_final_text")

    def drawLocalDeath(self, snake, snake_lose):
        self.c.delete('score')
        self.c.bind("<Key>", self.main_menu)
        text = f"Выиграл игрок {snake.number+1}!"
        score = f"Его счёт: {snake.score}"
        Client.save_local_stats(snake, snake_lose)
        self.c.create_text(WIDTH // 2, HEIGHT // 2, text=text, fill='red', font="Arial 15", tag="solo_final_text")
        self.c.create_text(WIDTH // 2, HEIGHT // 2+20, text=score, fill='red', font="Arial 15", tag="solo_final_text")
        self.c.create_text(WIDTH // 2, HEIGHT // 2 + 50, text=f"Нажмите любую клавишу для продолжения...", fill='red',
                           font="Arial 12", tag="solo_final_text")

    
    # Отрисовка игрового поля
    def drawDesk(self):
        self.c.pack(expand=1, fill='both')
        self.c.focus_set()
        self.drawScore()

    def drawOnlineApple(self, cords_of_apple):
        try:
            self.c.delete('online_apple')
        except: pass
        self.c.create_oval(cords_of_apple[0], cords_of_apple[1], cords_of_apple[2], cords_of_apple[3], fill='blue', tag='online_apple')

    # отрисовка счёта второго игрока при игре онлайн
    def drawOnlineScore(self, value):
        try:
            self.c.delete('online_score')
        except: pass
        self.c.create_text(WIDTH - 80, 10, text=f"Счёт игрока 2: {value}", fill='white', font="Arial 15",
                           tag='online_score')

    def drawOnlineSnake(self, cords):
        try:
            self.c.delete('online_snake')
        except: pass
        for cord in cords:
            self.c.create_rectangle(cord[0], cord[1], cord[2], cord[3], fill="white", tag="online_snake")

def get_key(d: dict, value: tuple) -> str:
    for k, v in d.items():
        if v == value:
            return k

def start_solo_game():
    global snake
    global snake_2
    global apple
    root.restart()

    snake_2 = None

    snake = Snake([Segment(7, 15, root.c, color='black'), Segment(7, 16, root.c)], canvas=root.c)
    apple = Apple(root.c)
    root.drawDesk()
    root.c.bind("<Key-w>", snake.change_direction)
    root.c.bind("<Key-a>", snake.change_direction)
    root.c.bind("<Key-s>", snake.change_direction)
    root.c.bind("<Key-d>", snake.change_direction)

def start_online_game():
    global snake
    global apple
    for key in root.widgets:
        root.widgets[key].pack_forget()

    root.c.delete('solo_final_text')
    root.c.delete('segment')
    root.c.delete('apple')

    if root.is_server:
        snake = Snake([Segment(7, 15, root.c, color='black'), Segment(7, 16, root.c)], canvas=root.c, number=0)
    else:
        snake = Snake([Segment(9, 1, root.c, color='black'), Segment(9, 0, root.c)], canvas=root.c, number=1, default_direction='s')

    root.drawDesk()
    root.drawOnlineScore(0)

    apple = Apple(root.c)

    root.c.bind("<Key-w>", snake.change_direction)
    root.c.bind("<Key-a>", snake.change_direction)
    root.c.bind("<Key-s>", snake.change_direction)
    root.c.bind("<Key-d>", snake.change_direction)
    snake.all_good = True
    snake.move()

def start_local_game():
    # 15x - центр поля/16x - самое право| 16y - самый низ поля
    global snake
    global snake_2
    global apple
    root.restart()

    apple = Apple(root.c)

    snake = Snake([Segment(7, 15, root.c, color='black'), Segment(7, 16, root.c)], canvas=root.c, number=0)
    snake_2 = Snake([Segment(9, 1, root.c, color='white'), Segment(9, 0, root.c, color='black')], canvas=root.c, number=1, default_direction='s')

    snake_2.directions = {
        "Up": (0, -1),
        "Down": (0, 1),
        "Left": (-1, 0),
        "Right": (1, 0)
    }

    root.drawDesk()
    root.c.bind("<Key-Up>", snake_2.change_direction)
    root.c.bind("<Key-Down>", snake_2.change_direction)
    root.c.bind("<Key-Right>", snake_2.change_direction)
    root.c.bind("<Key-Left>", snake_2.change_direction)

    root.c.bind("<Key-w>", snake.change_direction)
    root.c.bind("<Key-a>", snake.change_direction)
    root.c.bind("<Key-s>", snake.change_direction)
    root.c.bind("<Key-d>", snake.change_direction)

def ready(is_server=True):
    if is_server:
        if root.ready_var.get() == 1:
            root.server.ready = "ready"
            root.server.user.conn.send("ready".encode('utf-8'))
            root.widgets["player1"]["text"] = "Игрок 1 (Хост) | Готов"
            if root.server.user.ready == "ready":
                start_online_game()
        else:
            root.server.ready = "unready"
            root.server.user.conn.send("unready".encode('utf-8'))
            root.widgets["player1"]["text"] = "Игрок 1 (Хост) | Не готов"
    else:
        if root.ready_var.get() == 1:
            root.server.user.ready = "ready"
            root.server.server.send("ready".encode('utf-8'))
            root.widgets["player2"]["text"] = "Игрок 2 (Подключившийся) | Готов"
            if root.server.ready == "ready":
                start_online_game()
        else:
            root.server.user.ready = "unready"
            root.server.server.send("unready".encode('utf-8'))
            root.widgets["player2"]["text"] = "Игрок 2 (Подключившийся) | Не готов"

if __name__ == "__main__":
    root = Desk()

    snake = None
    snake_2 = None
    apple = None

    root.main_menu()

    root.mainloop()