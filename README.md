# tfm-botnet
Piloto experimental TFM - Infiltración en redes botnet como estrategia defensiva: un análisis experimental basado en tráfico de red

Simulación controlada de la degradación funcional de botnets por infiltración de nodos, comparando una arquitectura centralizada (C&C) y una P2P en un entorno emulado con Mininet. Proyecto desarrollado para un Trabajo de Fin de Máster en Ciberseguridad.

Trabajo académico y defensivo. La ejecución se realiza en un entorno local y aislado, con mensajes sintéticos benignos. No contiene malware real ni capacidades ofensivas; su objetivo es medir la degradación del rendimiento de la red.

## Contenido del repositorio

### `scripts/` — Código del piloto

**Topologías de red (Mininet)**
- `topology_centralized.py` — topología centralizada: 40 bots y un servidor C2 sobre un conmutador; cuello de botella en el enlace del C2.
- `topology_p2p.py` — topología P2P: 4 conmutadores en cadena con los bots repartidos; cuello de botella en los enlaces troncales.

**Componentes de la simulación**
- `c2_server.py` — servidor de mando y control (arquitectura centralizada).
- `normal_bot_centralized.py` / `normal_bot_p2p.py` — bots legítimos de cada arquitectura.
- `infiltrated_bot_centralized.py` / `infiltrated_bot_p2p.py` — nodos infiltrados que saturan el canal con tráfico de relleno.

**Ejecución y análisis**
- `run_experiment.py` — coordinador de las ejecuciones: levanta la topología, lanza los procesos, captura el tráfico (tcpdump) y mide latencia/pérdida (ping) y throughput (iperf3).
- `extract_metrics.py` — procesa las capturas y los registros y genera el CSV de métricas.
- `data_tables.py` — genera las tablas de resultados a partir del CSV.
- `plot_results.py` — genera las figuras del análisis.
- `centralizada_topologia.py` / `P2P_topologia.py` — generan los diagramas de las topologías.

### `captures/{centralized,p2p}/` — Capturas de tráfico
- Archivos `.pcap` de cada ejecución.
- pcaps de centralized y p2p comprimidos con 7z para poder subirlos a Github debido a su tamaño (captures/{centralized.7z,p2p.7z}).

### `logs/{centralized,p2p}/` — Registros
- Salidas de ping, iperf3 y de los procesos de cada ejecución.
- logs de centralized y p2p comprimidos con 7z para poder subirlos a Github debido al gran número de archivos (logs/{centralized.7z,p2p.7z})

### `results/` — Resultados
- `csv/` — `metrics_summary.csv` (métricas consolidadas de las 24 ejecuciones) y las tablas de resultados.
- `figures/` — figuras generadas (métricas frente al nivel de infiltración y diagramas de topología).

## Diseño experimental

40 bots, cuatro niveles de infiltración (0 %, 10 %, 25 % y 50 %), dos arquitecturas y
tres repeticiones por escenario: **24 ejecuciones** en total. De cada una se obtienen
cinco métricas: latencia, throughput, pérdida de paquetes, tráfico total generado y
estabilidad de la comunicación.
