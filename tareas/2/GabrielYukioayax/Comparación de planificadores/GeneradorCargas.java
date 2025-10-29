import java.util.*;

public class GeneradorCargas{

    public static final class Config{
        public int nMin = 1, nMax = 1;
        public int servicioMin = 1, servicioMax = 1;

        public Dist distServicio = Dist.UNIFORM; 
        public double expServicioMedia = 4.0;

        public Dist distLlegada = Dist.UNIFORM; 
        public double expLlegadaMedia = 3.0;

        public Integer maxLlegadaFijo = null;   
        public int gapLlegadas = 0;     

        public boolean ordenarPorLlegada = true;
        public boolean nombresSecuenciales = true;
    }
    public enum Dist { UNIFORM, EXP }

    public static List<ProcesoDefinicion> generarRonda(Random rnd, Config cfg){
        if(cfg.nMax < cfg.nMin) throw new IllegalArgumentException("nMax < nMin");
        if(cfg.servicioMax < cfg.servicioMin) throw new IllegalArgumentException("servicioMax < servicioMin");

        int n = cfg.nMin + rnd.nextInt(cfg.nMax - cfg.nMin + 1);
        int maxLlegada = (cfg.maxLlegadaFijo != null) ? cfg.maxLlegadaFijo : (n + Math.max(0, cfg.gapLlegadas));

        List<ProcesoDefinicion> defs = new ArrayList<>(n);
        for(int i=0;i<n;i++){
            String id = cfg.nombresSecuenciales ? idSecuencial(i) : "P"+(i+1);
            int llegada  = clamp(draw(rnd, cfg.distLlegada,  0, maxLlegada, cfg.expLlegadaMedia),  0, maxLlegada);
            int servicio = clamp(draw(rnd, cfg.distServicio, cfg.servicioMin, cfg.servicioMax, cfg.expServicioMedia), cfg.servicioMin, cfg.servicioMax);
            if(servicio<=0) servicio = 1;
            defs.add(new ProcesoDefinicion(id, llegada, servicio));
        }
        if(cfg.ordenarPorLlegada){
            defs.sort(Comparator.<ProcesoDefinicion>comparingInt(d->d.llegada).thenComparing(d->d.id));
        }
        return defs;
    }

    private static int draw(Random rnd, Dist dist, int min, int max, double mu){
        switch(dist){
            case UNIFORM: return min + rnd.nextInt((max - min) + 1);
            case EXP:
                double u = Math.max(1e-12, rnd.nextDouble());
                double x = -mu * Math.log(u);
                return clamp((int)Math.round(x), min, max);
            default: return min;
        }
    }

    private static int clamp(int v,int lo,int hi){ return v<lo?lo:(v>hi?hi:v); }

    private static String idSecuencial(int idx){
        StringBuilder sb = new StringBuilder();
        do{
            int r = idx % 26;
            sb.append((char)('A'+r));
            idx = (idx / 26) - 1;
        }while(idx >= 0);
        return sb.reverse().toString();
    }
}
