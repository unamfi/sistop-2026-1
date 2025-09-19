public class SimulacionPresa {

    public static void main(String[] args) {
        Presa presa = new Presa(100, 20);

        // Crear e iniciar los hilos para el flujo del río y del desagüe
        Thread hiloRio = new FlujoRio(presa);
        Thread hiloDesague = new FlujoDesague(presa);

        hiloRio.start();
        hiloDesague.start();

        // Mantener la simulación en ejecución
        try {
            hiloRio.join();
            hiloDesague.join();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }

    static class Presa {
        private double nivelAgua;
        private final double nivelMaximo;
        private final double nivelMinimo;
        private boolean compuertasAbiertas;

        public Presa(double nivelMaximo, double nivelMinimo) {
            this.nivelAgua = 0.0;
            this.nivelMaximo = nivelMaximo;
            this.nivelMinimo = nivelMinimo;
            this.compuertasAbiertas = false;
        }

        private String formatoDecimal(double valor) {
            return String.format("%.2f", valor);
        }

        public synchronized void ajustarNivel(double flujo) {
            nivelAgua += flujo;
            if (nivelAgua < 0) nivelAgua = 0;

            // Verificar y ajustar el estado de las compuertas
            if (nivelAgua >= nivelMaximo) {
                compuertasAbiertas = true;
                System.out.println("Presa al borde: Se abren las compuertas. Nivel: " + formatoDecimal(nivelAgua));
            } else if (nivelAgua <= nivelMinimo) {
                compuertasAbiertas = false;
                System.out.println("Nivel bajo: Se cierran las compuertas. Nivel: " + formatoDecimal(nivelAgua));
            } else {
                System.out.println("Nivel actual de agua: " + formatoDecimal(nivelAgua));
            }

            // Verificar si la presa se desbordó
            if (nivelAgua > nivelMaximo + 5) {
                System.out.println("Presa desbordada! Nivel: " + formatoDecimal(nivelAgua));
                System.exit(0);
            }
        }

        public synchronized boolean estanCompuertasAbiertas() {
            return compuertasAbiertas;
        }
    }

    static class FlujoRio extends Thread {
        private final Presa presa;

        public FlujoRio(Presa presa) {
            this.presa = presa;
        }

        @Override
        public void run() {
            while (true) {
                double flujo = 10 + Math.random() * 5; // Flujo del río entre 10 y 15
                System.out.println("----------------");
                System.out.println("Flujo del río: " + String.format("%.2f", flujo));
                presa.ajustarNivel(flujo);

                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        }
    }

    static class FlujoDesague extends Thread {
        private final Presa presa;

        public FlujoDesague(Presa presa) {
            this.presa = presa;
        }

        @Override
        public void run() {
            while (true) {
                if (presa.estanCompuertasAbiertas()) {
                    double flujo = 12 + Math.random() * 5; // Flujo del desagüe entre 12 y 17
                    //System.out.println("Flujo del desagüe: " + String.format("%.2f", flujo));
                    presa.ajustarNivel(-flujo);
                } else {
                    //System.out.println("Compuertas cerradas: No hay flujo de desagüe.");
                }

                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        }
    }
}