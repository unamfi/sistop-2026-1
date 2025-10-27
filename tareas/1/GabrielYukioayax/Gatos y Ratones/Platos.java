import java.util.concurrent.ArrayBlockingQueue;

// Se administra los p platos disponibles
public class Platos{
    private final ArrayBlockingQueue<Integer> libres;

    public Platos(int p){
        this.libres = new ArrayBlockingQueue<>(p);
        for(int i=1;i<=p;i++) libres.add(i);
    }

    public int reservar(){
        Integer id = libres.poll();
        return (id==null) ? -1 : id;
    }

    public void devolver(int id){
        libres.offer(id);
    }

    public int disponibles(){
        return libres.size();
    }
}
