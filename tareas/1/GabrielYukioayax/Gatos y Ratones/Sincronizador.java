import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.ReentrantLock;

// Se coordina turnos entre especies
public class Sincronizador{
    private final ReentrantLock lock = new ReentrantLock(true);
    private final Condition condGatos = lock.newCondition();
    private final Condition condRatones = lock.newCondition();

    private final Platos platos;

    // Estado compartido
    private Especie comiendo = Especie.NADIE;
    private Especie proximoTurno = Especie.GATOS;

    private int gatosComiendo = 0, ratonesComiendo = 0;
    private int gatosEsperando = 0, ratonesEsperando = 0;

    public Sincronizador(Platos platos){
        this.platos = platos;
    }

    // Entrada de gato, devuelve id de plato reservado
    public int entrarGato() throws InterruptedException{
        lock.lock();
        try{
            gatosEsperando++;
            while(!(proximoTurno==Especie.GATOS && ratonesComiendo==0 && platos.disponibles()>0)
                  || (comiendo==Especie.RATONES)){
                condGatos.await();
            }
            int plato = platos.reservar();
            while(plato==-1){
                condGatos.await();
                plato = platos.reservar();
            }
            gatosEsperando--;
            gatosComiendo++;
            comiendo = Especie.GATOS;
            return plato;
        } finally{
            lock.unlock();
        }
    }

    public void salirGato(int plato){
        platos.devolver(plato);
        lock.lock();
        try{
            gatosComiendo--;
            if(gatosComiendo==0){
                comiendo = Especie.NADIE;
                if(ratonesEsperando>0) proximoTurno = Especie.RATONES;
                notificarSegunTurno();
            } else{
                condGatos.signalAll();
            }
        } finally{
            lock.unlock();
        }
    }

    // Entrada de ratón, devuelve id de plato reservado
    public int entrarRaton() throws InterruptedException{
        lock.lock();
        try{
            ratonesEsperando++;
            while(!(proximoTurno==Especie.RATONES && gatosComiendo==0 && platos.disponibles()>0)
                  || (comiendo==Especie.GATOS)){
                condRatones.await();
            }
            int plato = platos.reservar();
            while(plato==-1){
                condRatones.await();
                plato = platos.reservar();
            }
            ratonesEsperando--;
            ratonesComiendo++;
            comiendo = Especie.RATONES;
            return plato;
        } finally{
            lock.unlock();
        }
    }

    public void salirRaton(int plato){
        platos.devolver(plato);
        lock.lock();
        try{
            ratonesComiendo--;
            if(ratonesComiendo==0){
                comiendo = Especie.NADIE;
                if(gatosEsperando>0) proximoTurno = Especie.GATOS;
                notificarSegunTurno();
            } else{
                condRatones.signalAll();
            }
        } finally{
            lock.unlock();
        }
    }

    private void notificarSegunTurno(){
        if(proximoTurno==Especie.GATOS) condGatos.signalAll();
        else if(proximoTurno==Especie.RATONES) condRatones.signalAll();
    }
}
