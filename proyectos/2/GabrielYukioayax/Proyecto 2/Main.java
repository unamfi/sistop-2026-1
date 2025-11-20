import javax.swing.SwingUtilities;
public class Main{
    public static void main(String[] args){
        //Iniciar la interfaz grafica
        SwingUtilities.invokeLater(new Runnable(){
            public void run(){
                try {
                    //Creamos y mostramos la ventana
                    InterfazGrafica ventana = new InterfazGrafica();
                    ventana.setVisible(true);
                } catch (Exception e){
                    e.printStackTrace();
                }
            }
        });
    }
}