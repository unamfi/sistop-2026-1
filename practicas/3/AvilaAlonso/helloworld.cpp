#include <iostream>
#include <string>

int main() {
  std::cout << "Ingrese su nombre\n" << std::endl;
  std::string nombre;
  std::cin>>nombre;

  std::cout << "Hola " + nombre + "!" << std::endl;

  return 0;
}