// Punto de entrada o main (g=gatos, r=ratones, p=platos, rondas por hilo)

public class GatosyRatones{
    public static void main(String[] args) throws Exception{
        int g = (args.length>=1)?Integer.parseInt(args[0]):3;
        int r = (args.length>=2)?Integer.parseInt(args[1]):5;
        int p = (args.length>=3)?Integer.parseInt(args[2]):2;
        int rondas = (args.length>=4)?Integer.parseInt(args[3]):3;

        Platos platos = new Platos(p);
        Sincronizador sync = new Sincronizador(platos);

        Thread[] hilos = new Thread[g+r];
        for(int i=0;i<g;i++) hilos[i] = new Thread(new Gato(i+1,rondas,sync));
        for(int i=0;i<r;i++) hilos[g+i] = new Thread(new Raton(i+1,rondas,sync));

        System.out.printf("Inicio: g=%d, r=%d, p=%d, rondas=%d%n",g,r,p,rondas);
        for(Thread t:hilos) t.start();
        for(Thread t:hilos) t.join();
        System.out.println("Simulación terminada.");
    }
}
