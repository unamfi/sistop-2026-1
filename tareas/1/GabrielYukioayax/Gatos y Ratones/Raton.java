import java.util.Random;

// Respeta turno, toma plato y libera
public class Raton implements Runnable{
    private final int id;
    private final int rondas;
    private final Sincronizador sync;
    private final Random rnd = new Random();

    public Raton(int id,int rondas,Sincronizador sync){
        this.id = id;
        this.rondas = rondas;
        this.sync = sync;
    }

    @Override
    public void run(){
        for(int i=1;i<=rondas;i++){
            try{
                int plato = sync.entrarRaton();
                System.out.printf("Ratón %d comiendo en plato %d (ronda %d)%n",id,plato,i);
                Thread.sleep(100+rnd.nextInt(200));
                sync.salirRaton(plato);
                System.out.printf("Ratón %d dejó libre el plato %d%n",id,plato);
                Thread.sleep(50+rnd.nextInt(120));
            } catch(InterruptedException e){
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
}
