import java.util.List;

public class Impresor{

    private static final String[] ORD = {
        "Primera","Segunda","Tercera","Cuarta","Quinta",
        "Sexta","Séptima","Octava","Novena","Décima"
    };

    private static String ordinalEs(int idx){
        if (idx>=0 && idx<ORD.length) return ORD[idx];
        return (idx+1) + "ª";
    }

    public static void imprimirEncabezadoRonda(int indice,List<ProcesoDefinicion> defs){
        System.out.println("- " + ordinalEs(indice) + " ronda:");
        StringBuilder sb = new StringBuilder("  ");
        for(int i=0;i<defs.size();i++){
            ProcesoDefinicion d = defs.get(i);
            sb.append(d.id).append(": ").append(d.llegada).append(", t=").append(d.servicio);
            if(i<defs.size()-1) sb.append("; ");
        }
        System.out.println(sb.toString());
        System.out.println("      (tot:"+ Utilidades.servicioTotal(defs) +")");
    }

    public static void imprimirMetricaYEsquema(String nombre, ResultadoSimulacion r, int ancho){
        String etiqueta = String.format("%-"+ancho+"s", nombre + ":");
        System.out.println(etiqueta+" T="+Utilidades.f1(r.promedioT)+", E="+Utilidades.f1(r.promedioE)+", P="+Utilidades.f2(r.promedioP));
        System.out.println(r.lineaTiempo);
    }
}
