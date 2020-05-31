FILENAME_INTERACTED_USERS = "interacted_users.txt"


class Storage:
    interacted_users_list = []

    def __init__(self):
        file_interacted_users = open(FILENAME_INTERACTED_USERS, "a+")
        file_interacted_users.seek(0)
        for line in file_interacted_users.readlines():
            self.interacted_users_list.append(line.strip())
        file_interacted_users.close()

    def check_user_was_interacted(self, username):
        return username in self.interacted_users_list

    def add_interacted_user(self, username):
        self.interacted_users_list.append(username)
        file_interacted_users = open(FILENAME_INTERACTED_USERS, "a")
        file_interacted_users.write(username + '\n')
        file_interacted_users.close()
