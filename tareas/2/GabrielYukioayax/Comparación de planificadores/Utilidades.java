import java.util.*;
import java.util.stream.Collectors;

public class Utilidades {

    public static String f1(double x){ return String.format(Locale.US,"%.1f",x); }
    public static String f2(double x) { return String.format(Locale.US, "%.2f", x); }

    public static List<Proceso> clonar(List<ProcesoDefinicion> defs){
        List<Proceso> r = new ArrayList<>(defs.size());
        for(ProcesoDefinicion d: defs) r.add(new Proceso(d));
        return r;
    }

    public static int servicioTotal(List<ProcesoDefinicion> defs){
        int s=0; for(ProcesoDefinicion d: defs) s+=d.servicio; return s;
    }

    public static boolean todosTerminados(List<Proceso> ps){
        for(Proceso p: ps) if(p.restante>0) return false;
        return true;
    }

    public static Comparator<Proceso> porId(){ return Comparator.comparing(p -> p.id); }

    public static void establecerFinalizado(Proceso p,int tDespues){
        if(p.restante==0 && p.completado==null) p.completado = tDespues;
    }

    public static ResultadoSimulacion metricas(List<Proceso> ps,String linea){
        double sumT=0, sumE=0, sumP=0; int n=ps.size();
        for(Proceso p: ps){
            int C = (p.completado==null)? 0 : p.completado;
            int T = C - p.llegada;
            int E = T - p.servicio;
            double P = (double)T / (double)p.servicio;
            sumT+=T; sumE+=E; sumP+=P;
        }
        return new ResultadoSimulacion(sumT/n, sumE/n, sumP/n, linea);
    }

   
    public static void encolarLlegadas(List<Proceso> ps,int tiempo,Deque<Proceso> cola){
        List<Proceso> llegados = ps.stream()
                .filter(p -> p.llegada==tiempo)
                .sorted(porId())
                .collect(Collectors.toList());
        for(Proceso p: llegados) cola.addLast(p);
    }
}
