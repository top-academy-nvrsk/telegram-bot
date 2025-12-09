import requests

# взаимодействия с api
class DatingAPI:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_user(self, tg_id):
        return requests.get(f'{self.base_url}/users/{tg_id}')

    def create_user(self, data):
        return requests.post(f"{self.base_url}/users", json=data)

    def create_anquette(self, data):
        return requests.post(f"{self.base_url}/anquettes", json=data)

    def get_anquette(self, anq_id):
        return requests.get(f"{self.base_url}/anquettes/{anq_id}")

    def delete_anquette(self, anq_id):
        return requests.delete(f"{self.base_url}/anquettes/{anq_id}")

    def update_user(self, tg_id, data):
        return requests.put(f"{self.base_url}/users/{tg_id}", json=data)

    def update_anquette(self, anq_id, data):
        return requests.put(f"{self.base_url}/anquettes/{anq_id}", json=data)