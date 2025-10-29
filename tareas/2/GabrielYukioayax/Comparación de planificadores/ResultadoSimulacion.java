public class ResultadoSimulacion{
    public final double promedioT; 
    public final double promedioE;
    public final double promedioP;
    public final String lineaTiempo;

    public ResultadoSimulacion(double promedioT,double promedioE,double promedioP,String lineaTiempo){
        this.promedioT = promedioT; 
        this.promedioE = promedioE; 
        this.promedioP = promedioP; 
        this.lineaTiempo = lineaTiempo;
    }
}
