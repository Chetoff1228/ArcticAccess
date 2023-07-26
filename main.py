import streamlit as st
from app import home, registration, about, algorithm

# Глобальная переменная для хранения статуса входа или регистрации
def read_login_status():
    with open('login_status.txt', 'r') as file:
        lines = file.readlines()
        successful_login = int(lines[0].strip())
        successful_registration = int(lines[1].strip())
    return successful_login, successful_registration

def create_login_status_file():
    status_data = "0\n0"
    with open("login_status.txt", "w") as file:
        file.write(status_data)
        
# Глобальные переменные для хранения статуса входа и регистрации
logged_in, registered = 0, 0

# Базовое меню
st.title('UrbanMapMasters от Arctic Access')

# Вход выполнен, отображение меню и выбор раздела
menu = ['Главная', 'Вход/Регистрация', 'Старт', 'О проекте']
choice = st.sidebar.selectbox('Меню', menu)

if choice == 'Главная':
    home.show()

elif choice == 'Вход/Регистрация':
    create_login_status_file()
    registration.show()
    
elif choice == 'О проекте':
    about.show()

elif choice == 'Старт':
    logged_in, registered = read_login_status()
    print(logged_in, registered)
    if not registered and not logged_in:
        st.warning("Пожалуйста, войдите или зарегистрируйтесь для доступа к разделу 'Старт'")
    if logged_in or registered:
        algorithm.show()