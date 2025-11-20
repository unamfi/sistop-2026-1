import java.util.*;
import java.nio.file.*;
import java.io.*;

public class Simulador{
    private static void helpAndExit(String msg){
        if(msg!=null && !msg.isBlank()) System.err.println("Error: "+msg);
        System.err.println(
            "Uso:\n"+
            "  java Simulador --alg <lista> [ALGS_OPTS] ( --from \"A:0,3;B:1,5;...\" | --from-file <path> | --random GEN_OPTS -n N ) [-s SEED]\n\n"+
            "  --alg fcfs,spn,rr,mlfq     Algoritmos a ejecutar (al menos uno)\n"+
            "  RR:    --rr q1,q2,...      Quantums requeridos si usas rr\n"+
            "  MLFQ:  --mlfq q1,q2,...    Quantums por nivel (usa -1 para infinito)\n"+
            "         --mlfq-aging T      Ticks de espera para promover (opcional)\n"+
            "         --mlfq-no-preempt   Sin desalojo por nivel superior (opcional)\n"+
            "\n"+
            "  Origen de procesos (elige uno):\n"+
            "    --from \"A:0,3;B:1,5;...\"  (puedes repetir --from para múltiples rondas)\n"+
            "    --from-file <path>         (una línea = una ronda con el mismo formato)\n"+
            "    --random GEN_OPTS -n N     (N rondas aleatorias, semilla opcional)\n"+
            "\n"+
            "  GEN_OPTS (si usas --random):\n"+
            "    --gen-n-min X --gen-n-max Y\n"+
            "    --gen-serv-min A --gen-serv-max B\n"+
            "    --gen-serv-dist uniform | exp:MU\n"+
            "    --gen-arr-dist uniform | exp:MU\n"+
            "    --gen-gap G                (maxLlegada = n + G)\n"+
            "    --gen-max-lleg M           (fija maxLlegada; ignora gap)\n"+
            "\n"+
            "  -s SEED  Semilla para reproducibilidad\n"
        );
        System.exit(1);
    }

    private static List<ProcesoDefinicion> parseSet(String spec){
        List<ProcesoDefinicion> r = new ArrayList<>();
        String[] parts = spec.split(";");
        for(String raw: parts){
            String s = raw.trim();
            if(s.isEmpty()) continue;
            String[] kv = s.split(":",2);
            if(kv.length!=2) throw new IllegalArgumentException("Entrada inválida (falta ':'): "+s);
            String id = kv[0].trim();
            String rest = kv[1].toLowerCase(Locale.ROOT).replace("t=","").replace(" ","");
            String[] nums = rest.split(",",2);
            if(nums.length!=2) throw new IllegalArgumentException("Entrada inválida (llegada,servicio): "+s);
            int llegada = Integer.parseInt(nums[0].trim());
            int servicio = Integer.parseInt(nums[1].trim());
            if(servicio<=0) throw new IllegalArgumentException("Servicio debe ser >0 en: "+s);
            r.add(new ProcesoDefinicion(id, llegada, servicio));
        }
        r.sort(Comparator.<ProcesoDefinicion>comparingInt(d->d.llegada).thenComparing(d->d.id));
        return r;
    }

    private static List<List<ProcesoDefinicion>> parseFile(String path) throws IOException{
        List<List<ProcesoDefinicion>> rondas = new ArrayList<>();
        try(BufferedReader br = Files.newBufferedReader(Paths.get(path))){
            String line;
            while((line = br.readLine())!=null){
                String s = line.trim();
                if(s.isEmpty() || s.startsWith("#")) continue;
                rondas.add(parseSet(s));
            }
        }
        if(rondas.isEmpty()) throw new IllegalArgumentException("El archivo no contiene rondas válidas.");
        return rondas;
    }

    private static GeneradorCargas.Config parseGenArgs(String[] args){
        GeneradorCargas.Config g = new GeneradorCargas.Config();
        for(int i=0;i<args.length;i++){
            switch(args[i]){
                case "--gen-n-min":     g.nMin = Integer.parseInt(args[++i]); break;
                case "--gen-n-max":     g.nMax = Integer.parseInt(args[++i]); break;
                case "--gen-serv-min":  g.servicioMin = Integer.parseInt(args[++i]); break;
                case "--gen-serv-max":  g.servicioMax = Integer.parseInt(args[++i]); break;
                case "--gen-gap":       g.gapLlegadas = Integer.parseInt(args[++i]); g.maxLlegadaFijo=null; break;
                case "--gen-max-lleg":  g.maxLlegadaFijo = Integer.valueOf(args[++i]); break;
                case "--gen-serv-dist":{
                    String v = args[++i].toLowerCase(Locale.ROOT);
                    if(v.startsWith("uniform")) g.distServicio = GeneradorCargas.Dist.UNIFORM;
                    else if(v.startsWith("exp")){
                        g.distServicio = GeneradorCargas.Dist.EXP;
                        int p=v.indexOf(':'); if(p>0) g.expServicioMedia = Double.parseDouble(v.substring(p+1));
                    }
                    break;
                }
                case "--gen-arr-dist":{
                    String v = args[++i].toLowerCase(Locale.ROOT);
                    if(v.startsWith("uniform")) g.distLlegada = GeneradorCargas.Dist.UNIFORM;
                    else if(v.startsWith("exp")){
                        g.distLlegada = GeneradorCargas.Dist.EXP;
                        int p=v.indexOf(':'); if(p>0) g.expLlegadaMedia = Double.parseDouble(v.substring(p+1));
                    }
                    break;
                }
            }
        }
        return g;
    }

    private static PlanificadorMLFQ.Config parseMlfqConfig(String[] args){
        int[] quanta = null;
        boolean preempt = true;
        int aging = 0;
        for(int i=0;i<args.length;i++){
            switch(args[i]){
                case "--mlfq":
                    String[] toks = args[++i].split(",");
                    quanta = new int[toks.length];
                    for(int k=0;k<toks.length;k++){
                        quanta[k] = Integer.parseInt(toks[k].trim()); 
                    }
                    break;
                case "--mlfq-aging": aging = Integer.parseInt(args[++i]); break;
                case "--mlfq-no-preempt": preempt = false; break;
            }
        }
        if(quanta==null) helpAndExit("Usaste 'mlfq' en --alg pero no pasaste --mlfq q1,q2,...");
        return new PlanificadorMLFQ.Config(quanta, preempt, aging);
    }

    public static void main(String[] args){
        Set<String> algSel = new LinkedHashSet<>();
        for(int i=0;i<args.length;i++){
            if("--alg".equals(args[i]) && i+1<args.length){
                for(String a: args[++i].split(",")) if(!a.isBlank()) algSel.add(a.trim().toLowerCase(Locale.ROOT));
            }
        }
        if(algSel.isEmpty()) helpAndExit("Debes indicar al menos un algoritmo con --alg");

        boolean useRandom = false;
        List<List<ProcesoDefinicion>> rondasInput = new ArrayList<>();
        String fromFile = null;
        int rondasRandom = 0;
        Long semilla = null;

        for(int i=0;i<args.length;i++){
            switch(args[i]){
                case "--from":
                    if(i+1>=args.length) helpAndExit("Falta cadena para --from");
                    rondasInput.add(parseSet(args[++i]));
                    break;
                case "--from-file":
                    if(i+1>=args.length) helpAndExit("Falta ruta para --from-file");
                    fromFile = args[++i];
                    break;
                case "--random":
                    useRandom = true; break;
                case "-n":
                    rondasRandom = Integer.parseInt(args[++i]); break;
                case "-s":
                    semilla = Long.parseLong(args[++i]); break;
            }
        }

        if(fromFile!=null){
            try{
                rondasInput.addAll(parseFile(fromFile));
            }catch(Exception e){
                helpAndExit("No se pudo leer --from-file: "+e.getMessage());
            }
        }

        if(!useRandom && rondasInput.isEmpty()){
            helpAndExit("Debes indicar --from (una o varias), o --from-file, o bien --random + -n");
        }
        if(useRandom && rondasRandom<=0){
            helpAndExit("Con --random debes indicar -n N (N>0)");
        }

        Random rnd = (semilla==null)? new Random() : new Random(semilla);
        GeneradorCargas.Config genCfg = useRandom? parseGenArgs(args) : null;

        List<Planificador> algs = new ArrayList<>();
        int ancho = 0;

        if(algSel.contains("fcfs")){
            Planificador p = new PlanificadorFCFS();
            algs.add(p); ancho = Math.max(ancho, p.nombre().length()+1);
        }
        if(algSel.contains("spn")){
            Planificador p = new PlanificadorSPN();
            algs.add(p); ancho = Math.max(ancho, p.nombre().length()+1);
        }
        if(algSel.contains("rr")){
            List<Integer> rrQ = new ArrayList<>();
            for(int i=0;i<args.length;i++){
                if("--rr".equals(args[i]) && i+1<args.length){
                    for(String t: args[++i].split(",")){
                        if(!t.isBlank()) rrQ.add(Integer.parseInt(t.trim()));
                    }
                }
            }
            if(rrQ.isEmpty()) helpAndExit("Usaste 'rr' en --alg pero no pasaste --rr q1,q2,...");
            for(int q: rrQ){
                Planificador p = new PlanificadorRR(q);
                algs.add(p); ancho = Math.max(ancho, p.nombre().length()+1);
            }
        }
        if(algSel.contains("mlfq")){
            PlanificadorMLFQ.Config cfg = parseMlfqConfig(args);
            Planificador p = new PlanificadorMLFQ(cfg);
            algs.add(p); ancho = Math.max(ancho, p.nombre().length()+1);
        }

        List<List<ProcesoDefinicion>> rondas = new ArrayList<>();
        if(useRandom){
            for(int i=0;i<rondasRandom;i++){
                rondas.add( GeneradorCargas.generarRonda(rnd, genCfg) );
            }
        }else{
            rondas.addAll(rondasInput);
        }

        for(int r=0;r<rondas.size();r++){
            List<ProcesoDefinicion> defs = rondas.get(r);
            Impresor.imprimirEncabezadoRonda(r, defs);
            for(Planificador plan: algs){
                ResultadoSimulacion res = plan.simular(defs);
                Impresor.imprimirMetricaYEsquema(plan.nombre(), res, ancho);
            }
            System.out.println();
        }
    }
}
