#include <iostream>
#include <string>
using namespace std;
int main() {
    string nombre;

    cout << "Ingresa tu nombre: ";
    getline(cin, nombre);

    cout << "Hola, " << nombre << "! Bienvenido(a)." << endl;  //esta version saluda

    return 0;
}

