import java.util.Random;

// Hace rondas de comida respetando turno y platos
public class Gato implements Runnable{
    private final int id;
    private final int rondas;
    private final Sincronizador sync;
    private final Random rnd = new Random();

    public Gato(int id,int rondas,Sincronizador sync){
        this.id = id;
        this.rondas = rondas;
        this.sync = sync;
    }

    @Override
    public void run(){
        for(int i=1;i<=rondas;i++){
            try{
                int plato = sync.entrarGato();
                System.out.printf("Gato %d comiendo en plato %d (ronda %d)%n",id,plato,i);
                Thread.sleep(100+rnd.nextInt(200));
                sync.salirGato(plato);
                System.out.printf("Gato %d dejó libre el plato %d%n",id,plato);
                Thread.sleep(50+rnd.nextInt(120));
            } catch(InterruptedException e){
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
}
