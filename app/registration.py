import streamlit as st
import hashlib



def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(username):
    with open('users.txt', 'r') as file:
        for line in file:
            user, _ = line.strip().split(':')
            if user == username:
                return True
    return False

def register_user(username, password):
    hashed_password = hash_password(password)
    with open('users.txt', 'a') as file:
        file.write(f'{username}:{hashed_password}\n')

def verify_user(username, password):
    hashed_password = hash_password(password)
    with open('users.txt', 'r') as file:
        for line in file:
            user, passw = line.strip().split(':')
            if user == username and passw == hashed_password:
                return True
    return False

def save_login_status(successful_login, successful_registration):
    with open('login_status.txt', 'w') as file:
        file.write(f'{int(successful_login)}\n')
        file.write(f'{int(successful_registration)}\n')

def show():
    st.subheader('Вход или регистрация')
    st.write('Введите имя пользователя и пароль, чтобы войти или зарегистрироваться.')

    username = st.text_input('Имя пользователя')
    password = st.text_input('Пароль', type='password')

    successful_login = False
    successful_registration = False

    if st.button('Войти'):
        if not username or not password:
            st.warning('Пожалуйста, введите имя пользователя и пароль.')
        elif user_exists(username):
            if verify_user(username, password):
                st.success('Вход успешно выполнен.')
                st.write(f'Добро пожаловать, {username}!')
                successful_login = True
                print(successful_login)
                save_login_status(successful_login, successful_registration)
            else:
                st.error('Неверный пароль. Попробуйте снова.')
        else:
            st.warning('Пользователя с таким именем не существует. Пожалуйста, зарегистрируйтесь.')

    if st.button('Зарегистрироваться'):
        if not username or not password:
            st.warning('Пожалуйста, введите имя пользователя и пароль.')
        elif user_exists(username):
            st.error('Пользователь с таким именем уже существует.')
        else:
            register_user(username, password)
            st.success('Регистрация успешно завершена.')
            st.write(f'Добро пожаловать, {username}!')
            successful_registration = True
            save_login_status(successful_login, successful_registration)    