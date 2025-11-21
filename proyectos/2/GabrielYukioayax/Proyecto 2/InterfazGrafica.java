import javax.swing.*;
import java.awt.*;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.OutputStream;
import java.io.PrintStream;
public class InterfazGrafica extends JFrame{
    private GestorDisco gestor;
    private JTextArea consola; // Aqui saldran los logs
    public InterfazGrafica(){
        // Configuracion de la ventana
        setTitle("Explorador FiUnamFS");
        setSize(700, 500);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null); // Centrar en pantalla
        setLayout(new BorderLayout());
        //Inicializar el Gestor
        gestor = new GestorDisco("fiunamfs.img");
        boolean estado = gestor.iniciar();
        //Area de Texto
        consola = new JTextArea();
        consola.setEditable(false);
        consola.setBackground(Color.BLACK);
        consola.setForeground(Color.GREEN);
        consola.setFont(new Font("Consolas", Font.PLAIN, 14));
        JScrollPane scroll = new JScrollPane(consola);
        add(scroll, BorderLayout.CENTER);
        redirigirConsola();
        if (!estado){
            System.out.println("[ERRORCRITICO]: No se encontro 'fiunamfs.img'.");
        } else{
            System.out.println("--- SISTEMA FIUNAMFS MONTADO CORRECTAMENTE ---");
            System.out.println("Listo para operaciones.");
        }
        //Panel de Botones
        JPanel panelBotones = new JPanel();
        panelBotones.setLayout(new GridLayout(1, 5, 10, 10));
        panelBotones.setBackground(Color.DARK_GRAY);
        JButton btnListar = new JButton("Listar");
        JButton btnSacar = new JButton("Sacar Archivo");
        JButton btnMeter = new JButton("Meter Archivo");
        JButton btnEliminar = new JButton("Eliminar");
        JButton btnSalir = new JButton("Salir");
        //Estilo basico a los botones
        styleButton(btnListar);
        styleButton(btnSacar);
        styleButton(btnMeter);
        styleButton(btnEliminar);
        styleButton(btnSalir);
        //Acciones de los botones
        //Listar
        btnListar.addActionListener(new ActionListener(){
            @Override
            public void actionPerformed(ActionEvent e) {
                //Ejecutamos en un hilo aparte para no congelar la ventana
                new Thread(() -> {
                    System.out.println("\n>> Listando directorio...");
                    gestor.leerContenido();
                    System.out.println(">> Fin del listado.");
                }).start();
            }
        });
        //Sacar
        btnSacar.addActionListener(new ActionListener(){
            @Override
            public void actionPerformed(ActionEvent e){
                String nombre = JOptionPane.showInputDialog(null, "Nombre del archivo a extraer (ej: tarea.txt):");
                if (nombre != null && !nombre.isEmpty()) {
                    System.out.println("\n>> Intentando sacar: " + nombre);
                    String res = gestor.sacarArchivo(nombre);
                    System.out.println(res);
                    JOptionPane.showMessageDialog(null, res);
                }
            }
        });
        //Meter
        btnMeter.addActionListener(new ActionListener(){
            @Override
            public void actionPerformed(ActionEvent e){
                //Usamos un selector de archivos
                JFileChooser fileChooser = new JFileChooser();
                int seleccion = fileChooser.showOpenDialog(null);
                if (seleccion == JFileChooser.APPROVE_OPTION){
                    String ruta = fileChooser.getSelectedFile().getAbsolutePath();
                    System.out.println("\n>> Intentando importar desde: " + ruta);
                    String res = gestor.meterArchivo(ruta);
                    System.out.println(res);
                    JOptionPane.showMessageDialog(null, res);
                }
            }
        });
        //Eliminar
        btnEliminar.addActionListener(new ActionListener(){
            @Override
            public void actionPerformed(ActionEvent e){
                String nombre = JOptionPane.showInputDialog(null, "Nombre del archivo a borrar:");
                if (nombre != null && !nombre.isEmpty()) {
                    int confirm = JOptionPane.showConfirmDialog(null, "¿Seguro que quieres borrar " + nombre + "?");
                    if (confirm == JOptionPane.YES_OPTION) {
                        System.out.println("\n>> Borrando: " + nombre);
                        String res = gestor.eliminarArchivo(nombre);
                        System.out.println(res);
                    }
                }
            }
        });
        //Salir
        btnSalir.addActionListener(new ActionListener(){
            @Override
            public void actionPerformed(ActionEvent e){
                gestor.cerrar();
                System.exit(0);
            }
        });
        panelBotones.add(btnListar);
        panelBotones.add(btnSacar);
        panelBotones.add(btnMeter);
        panelBotones.add(btnEliminar);
        panelBotones.add(btnSalir);
        add(panelBotones, BorderLayout.NORTH);
    }
    //Metodo auxiliar para que los botones se vean decentes
    private void styleButton(JButton b) {
        b.setFocusPainted(false);
        b.setFont(new Font("Arial", Font.BOLD, 12));
        b.setBackground(Color.LIGHT_GRAY);
    }
    //Redirir todo lo que salga por System.out.println al JTextArea
    private void redirigirConsola(){
        PrintStream printStream = new PrintStream(new OutputStream() {
            @Override
            public void write(int b){
                //Redirige byte por byte
                consola.append(String.valueOf((char) b));
                //Hace autoscroll hacia abajo
                consola.setCaretPosition(consola.getDocument().getLength());
            }
            @Override
            public void write(byte[] b, int off, int len){
                String s = new String(b, off, len);
                consola.append(s);
                consola.setCaretPosition(consola.getDocument().getLength());
            }
        });
        //Reemplazamos la salida estandar de Java
        System.setOut(printStream);
        System.setErr(printStream); //Tambien los errores
    }
}