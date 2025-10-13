#include <stdio.h>

int main(){
	
	char m[150];
	printf("Holi profe, como se encuentra hoy?");
	fgets(m, sizeof(m), stdin);

	printf("Que bueno, que se encuentre %s/n ;)", m); //espero que la respuesta sea bien
	
	return 0;
}
