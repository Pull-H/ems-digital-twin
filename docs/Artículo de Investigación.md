## <a name="_77wr6ek12z10"></a>**Un gemelo digital basado en simulación para los servicios médicos de emergencia: despacho predictivo y relocalización dinámica de ambulancias**
## <a name="_m29g1eut1vre"></a>**A Simulation-Based Digital Twin for Emergency Medical Services: Predictive Dispatch and Dynamic Ambulance Reallocation**
## <a name="_g7akirtzgtc"></a>**Garcia Alayo Jack David, [**https://orcid.org/0009-0005-3038-242X**](https://orcid.org/0009-0005-3038-242X), [**jgarciaa@unitru.edu.pe**](mailto:jgarciaa@unitru.edu.pe) Pulache Quiroga Gerson Aldair, [**https://orcid.org/0009-0008-2898-161X**](https://orcid.org/0009-0008-2898-161X), [**gpulacheq@unitru.edu.pe**](mailto:gpulacheq@unitru.edu.pe), Juan Pedro Santos Fernadez, [**https://orcid.org/0000-0002-8882-9256**](https://orcid.org/0000-0002-8882-9256), [**jsantos@unitru.edu.pe**](mailto:jsantos@unitru.edu.pe)**
##
## <a name="_vmy9e6fdjiw1"></a><a name="_kfec2g821lc9"></a>**1. Resumen**

Este artículo presenta un gemelo digital basado en simulación para evaluar despacho predictivo y relocalización dinámica de ambulancias con datos históricos de Nueva York. Su finalidad es analizar si incorporar pronósticos de demanda modifica los tiempos de respuesta, la cobertura y las diferencias territoriales frente a una política reactiva por menor tiempo estimado de llegada. El estudio combina análisis retrospectivo y experimentación computacional, sin intervención en un servicio de emergencias real.

El sistema articula preparación de datos, predicción de llamadas por borough para la siguiente hora y simulación de políticas bajo condiciones equivalentes. El conjunto de origen comprende 405 998 incidentes de abril a junio de 2026, antes de aplicar criterios de limpieza y cohortes. La evaluación distingue error predictivo y desempeño simulado, e incorpora análisis de sensibilidad a los supuestos sobre recursos y tiempos. Como componente complementario, se contempla la evaluación de instrumentos de utilidad percibida e interpretación de resultados.

El aporte consiste en vincular la predicción con sus consecuencias para la asignación de recursos y su distribución territorial dentro de un entorno reproducible. Las conclusiones se circunscriben a los escenarios estudiados; no demuestran mejoras operativas reales ni efectos clínicos.

**Palabras clave:** gemelo digital, simulación, servicios médicos de emergencia, predicción de demanda, relocalización de ambulancias.

## <a name="_86f2xjifn94c"></a>**2. Antecedentes**
### <a name="_jgqxzkca4k2f"></a>**2.1. Desigualdades espaciales y socioeconómicas en la respuesta de los servicios médicos de emergencia**
Los servicios médicos de emergencia (Emergency Medical Services, EMS) constituyen un componente crítico de los sistemas de atención sanitaria debido a que la efectividad de la atención prehospitalaria depende mucho de la capacidad de movilizar recursos clínicos hacia los incidentes a tiempo. Esta dependencia es particularmente relevante en condiciones tiempo-dependientes, como el paro cardíaco extrahospitalario, los traumatismos graves y determinados eventos cerebrovasculares. En consecuencia, el tiempo de respuesta es uno de los indicadores operativos más utilizados para evaluar el desempeño de los EMS. Sin embargo, la evidencia disponible demuestra que este desempeño no se distribuye homogéneamente entre territorios ni grupos socioeconómicos.

Un estudio nacional realizado por [(Hsia et al., 2018)](https://doi.org/10.1001/jamanetworkopen.2018.5202), utilizando registros del National Emergency Medical Services Information System (NEMSIS) correspondientes a 63 600 pacientes con paro cardíaco extrahospitalario, identificó diferencias sistemáticas asociadas al nivel de ingreso del área de residencia. El tiempo total de EMS fue de 43.0 minutos en las zonas de menor ingreso frente a 37.5 minutos en las de mayor ingreso y, después del ajuste estadístico, los tiempos permanecieron aproximadamente un 10% más elevados en las comunidades de menores ingresos. Asimismo, las respuestas realizadas en áreas de mayores ingresos presentaron una mayor probabilidad de cumplir umbrales operativos de 8 y 15 minutos. Estos resultados proporcionan evidencia de que la accesibilidad temporal al sistema prehospitalario puede estar condicionada por características socioeconómicas territoriales y no exclusivamente por la gravedad clínica o la distancia física.

La evidencia más reciente confirma la persistencia del problema. [(Verma et al., 2023)](https://doi.org/10.1016/j.focus.2023.100129) analizaron 18 540 personas involucradas en accidentes vehiculares fatales en Estados Unidos y encontraron que los condados con mayores ingresos familiares presentaban tiempos de llegada de EMS aproximadamente 12% menores que los condados socioeconómicamente desfavorecidos. También observaron que la disponibilidad de centros de trauma y la ruralidad modificaban los intervalos de atención. Estos hallazgos muestran que la desigualdad en la respuesta de emergencia es multidimensional: la distribución de las ambulancias interactúa con la estructura vial, la disponibilidad hospitalaria, las características demográficas y las condiciones socioeconómicas del territorio.

Síntesis recientes de gran alcance han examinado esta evidencia. Mediante una revisión y un análisis temático basado en Latent Dirichlet Allocation, [(Soltani et al., 2026)](https://doi.org/10.1108/IJES-01-2025-0002) identificaron áreas relacionadas con la ubicación de ambulancias, mortalidad, estrategias de despliegue, desigualdades geográficas y socioeconómicas, y servicios especializados. Esta síntesis sitúa la accesibilidad territorial entre los aspectos relevantes de la planificación EMS, sin que ello permita atribuir beneficios clínicos al sistema de simulación de este estudio.

Desde una perspectiva de planificación, estos resultados cuestionan los enfoques que evalúan exclusivamente el desempeño agregado del sistema. Una reducción del tiempo medio de respuesta de una ciudad no implica necesariamente una mejora equitativa cuando determinados barrios continúan experimentando tiempos persistentemente superiores. Por ello, el problema de asignación de recursos EMS puede conceptualizarse como un problema conjunto de eficiencia y equidad espacial, en el que la optimización global debe acompañarse de métricas capaces de detectar diferencias sistemáticas entre grupos territoriales.

Esta interpretación está respaldada por trabajos recientes de optimización. [(Gago-Carro et al., 2024)](https://doi.org/10.1016/j.eswa.2024.123665), por ejemplo, formularon un modelo estocástico de localización y relocalización de ambulancias que incorpora explícitamente criterios de cobertura equitativa. Su aplicación al sistema vasco de emergencias mostró que era posible incrementar sustancialmente la cobertura de zonas rurales y aisladas asumiendo una reducción relativamente limitada del desempeño agregado. Esto demuestra que eficiencia y equidad no son necesariamente objetivos incompatibles, pero la equidad debe incorporarse explícitamente dentro de la función de decisión para evitar que las soluciones matemáticamente eficientes concentren los recursos en zonas de alta demanda.

A partir de la investigación de operaciones, se ha empezado a implementar la equidad a través de mecanismos claros para distribuir los recursos. [(Jagtenberg & Mason, 2020)](https://doi.org/10.1016/j.ejor.2019.08.003) evidenciaron que los mecanismos de reparto temporal (time sharing), que permiten que las ambulancias roten entre regiones, tienen el potencial de incrementar significativamente la equidad territorial, aunque a costa de una disminución limitada en la cobertura general. Este hallazgo complementa los modelos estocásticos de cobertura equitativa y demuestra que hay procedimientos realizables para convertir el principio normativo de equidad en decisiones operativas específicas.

En el presente estudio, estos antecedentes justifican complementar los indicadores globales con diferencias entre boroughs. El dataset no contiene ingresos ni quintiles socioeconómicos: la evaluación es territorial descriptiva, no una medición de inequidad socioeconómica ni una demostración de su reducción.

### <a name="_o13lgpa49ytk"></a>**2.2. Predicción espacio-temporal de la demanda EMS**
Una de las causas fundamentales de la ineficiencia de los esquemas estáticos de despacho es que la demanda de EMS no permanece constante en el espacio ni en el tiempo. El volumen y la ubicación de las llamadas cambian en función de la hora del día, día de la semana, densidad poblacional, movilidad urbana, eventos masivos, condiciones meteorológicas y otros determinantes contextuales. Por esta razón, mantener las ambulancias exclusivamente en bases predefinidas y reaccionar después de recibir una llamada puede generar áreas temporalmente desprotegidas.

La literatura sobre predicción de demanda ha comenzado a abordar este problema mediante métodos estadísticos y de aprendizaje automático. [(Monks et al., 2023)](https://doi.org/10.1186/s12911-023-02218-z) compararon métodos de pronóstico diario de llamadas que requieren ambulancias y realizaron validación externa en servicios de Inglaterra y Gales. Este antecedente respalda el uso de referencias sencillas, separación temporal de datos y evaluación fuera de entrenamiento; su horizonte diario no equivale al horizonte horario del presente estudio.

Más recientemente, [(Shahidian et al., 2025)](https://doi.org/10.1016/j.cie.2024.110765) compararon nueve algoritmos de aprendizaje automático para pronosticar demanda EMS a corto plazo. Los métodos basados en boosting, particularmente Gradient Boosting y AdaBoost, presentaron los mejores resultados y demostraron capacidad para anticipar tanto el volumen horario de llamadas por distrito como el número esperado de despachos desde diferentes bases. Los autores enfatizan que estos modelos pueden integrarse directamente con sistemas de programación, localización y relocalización de vehículos.

En América Latina, un trabajo reciente de [(Neira-Rodado et al., 2025)](https://doi.org/10.1016/j.heliyon.2025.e41904) mostró que los modelos de boosting funcionan bien en ciudades intermedias. En Barranquilla, Colombia, combinaron aprendizaje automático con análisis de señales y estadísticas para anticipar dónde y cuándo ocurrirán emergencias. Dividieron la ciudad en zonas y entrenaron un modelo XGBoost con series de tiempo; ese modelo superó a Random Forest, con mejoras de precisión de hasta 26.9% en algunas zonas y 16.4% en promedio. Además, el método resultó útil incluso con pocos datos en ciertas particiones. Los autores destacan que esta mejora puede servir directamente para decidir dónde ubicar, reubicar o despachar ambulancias, lo que respalda evaluar modelos predictivos frente a referencias, sin establecer de antemano que XGBoost sea el algoritmo adecuado para otro contexto.

Estos trabajos establecen una transición importante desde la gestión reactiva hacia una gestión predictiva del sistema EMS. No obstante, la predicción por sí misma no determina qué ambulancia debe desplazarse, hacia dónde debe hacerlo ni cómo debe modificarse la distribución de recursos para reducir simultáneamente el tiempo de respuesta y las desigualdades territoriales. En consecuencia, el valor operacional de la predicción depende de su integración con una segunda capa de decisión capaz de convertir las estimaciones de demanda futura en acciones concretas. En este estudio esa capa utiliza reglas heurísticas de despacho y relocalización, no un solucionador de optimización exacta.
### <a name="_pqc6mwwl76zl"></a>**2.3. Relocalización dinámica y optimización de ambulancias**
La relocalización dinámica consiste en modificar temporalmente la ubicación de las ambulancias disponibles con la finalidad de mantener o mejorar la cobertura ante cambios en el estado del sistema. [(Becker et al., 2023)](https://doi.org/10.1136/bmjopen-2023-073394), en una revisión de alcance que incluyó 21 investigaciones, identificaron un creciente desarrollo de modelos matemáticos para decidir la posición temporal de las ambulancias utilizando variables como demanda estimada, localización hospitalaria, distancia, condiciones geográficas y disponibilidad operativa. Sin embargo, la revisión encontró una limitación particularmente importante: prácticamente todos los trabajos habían sido evaluados mediante simulaciones y solo uno había realizado una evaluación prospectiva en condiciones reales.

[(Gendreau et al., 2001)](https://doi.org/10.1016/S0167-8191%2801%2900103-X) contribuyeron a las bases de la relocalización en tiempo real: plantearon un modelo dinámico que decide cómo redistribuir la flota según el estado actual del sistema. Su propuesta, basada en una heurística de búsqueda tabú paralela que calcula por adelantado distintos escenarios de reubicación entre llamadas, mostró mediante experimentos computacionales con datos reales de Montreal la factibilidad de calcular estrategias de redespliegue. Además, este trabajo dejó una distinción operativa fundamental: una cosa es decidir qué ambulancia atiende cada llamada y otra muy distinta decidir dónde ubicar las ambulancias disponibles. Esa separación entre asignación y redespliegue es la que estructura el presente marco de despacho predictivo.

Diferentes metodologías de investigación de operaciones han demostrado que la relocalización puede mejorar el desempeño del sistema. Los modelos incluyen programación lineal entera, programación estocástica, heurísticas, optimización multiobjetivo y simulación-optimización. Por ejemplo, los modelos basados en análisis de isócronas han mostrado capacidad para redistribuir ambulancias cuando el sistema se encuentra saturado, mientras que otros enfoques incorporan explícitamente variaciones temporales de demanda y tráfico.

La evidencia basada en datos de servicios reales incluye estudios de Singapur, aunque no todos corresponden a intervenciones operativas. Por un lado, [(Ong et al., 2010)](https://doi.org/10.1111/j.1553-2712.2010.00860.x) lograron reducir los tiempos de respuesta analizando el despliegue de ambulancias desde una perspectiva geoespacial y temporal. Por otro lado, [(Lam et al., 2015)](https://doi.org/10.1016/j.ajem.2014.10.044) evaluaron, mediante simulación de eventos discretos, planes dinámicos de realineación basados en la gestión del estado del sistema (*System Status Management*). Con esos planes, basados en programación matemática, consiguieron bajar la mediana de los tiempos de respuesta en aproximadamente 44 segundos frente a una política estática.

Un hallazgo especialmente importante para la práctica fue que los beneficios se mantenían incluso cuando solo se ejecutaba el 60% de los movimientos de relocalización recomendados. Este resultado simulado sugiere que determinadas políticas dinámicas pueden mantener ventajas frente al cumplimiento parcial por parte de los despachadores, algo muy relevante en la operación real, donde no siempre es posible seguir todas las sugerencias al pie de la letra.

[(Essus et al., 2024)](https://doi.org/10.1016/j.cie.2023.109823) avanzaron hacia una optimización en tiempo real combinando un modelo de decisión con una simulación de eventos discretos de alta resolución geográfica para la ciudad de Nueva York. En lugar de optimizar únicamente cobertura, incorporaron funciones relacionadas con supervivencia y equilibrio de carga entre ambulancias. El estudio evaluó la atención oportuna de emergencias críticas y la carga de trabajo dentro de su escenario de simulación. El estudio demuestra la utilidad de conectar continuamente el estado simulado del sistema con decisiones de relocalización.

No obstante, estas aproximaciones deben interpretarse según el proceso modelado, los datos disponibles y las condiciones experimentales. La conexión entre predicción, decisiones y simulación no garantiza por sí sola una mejora: es necesario evaluar si el pronóstico aporta utilidad a la política y cómo se distribuye territorialmente su desempeño. Esta es la comparación que aborda el presente estudio, sin incorporar funciones de supervivencia ni asumir resultados operativos reales.

### <a name="_7p6o5yecmczv"></a>**2.4. Gemelos digitales en transporte, ciudades y respuesta a emergencias**
El paradigma de Digital Twin ofrece una arquitectura capaz de integrar estos componentes dentro de una representación dinámica del sistema físico. A diferencia de un modelo de simulación estático, un gemelo digital se caracteriza por mantener una representación computacional actualizable del objeto, proceso o sistema físico mediante flujos de información, permitiendo monitorizar estados, analizar condiciones, predecir comportamientos y evaluar decisiones antes de aplicarlas.

[(Petri et al., 2023)](https://doi.org/10.1016/j.jii.2023.100445) sostienen que un Digital Twin debe representar no solo la geometría del sistema físico, sino también sus componentes, relaciones y comportamiento dinámico, de manera que pueda evaluar estrategias de respuesta frente a condiciones cambiantes. Aunque su aplicación se desarrolla en infraestructura y entorno construido, este principio es directamente transferible a un sistema EMS, donde ambulancias, estaciones, hospitales, red vial, tráfico, clima y demanda forman un sistema dinámico cuyas interacciones determinan el desempeño global.

[(Chen et al., 2024)](https://doi.org/10.1109/COMST.2023.3308717), desde el ámbito sanitario, estructuran los sistemas de gemelos digitales alrededor de cinco componentes: adquisición de datos, comunicación, computación, gestión de datos y análisis/toma de decisiones. Esta arquitectura resulta especialmente pertinente para un EMS Digital Twin porque establece una cadena desde la observación del sistema físico hasta la generación de acciones mediante modelos analíticos. Además, los autores destacan que el valor del gemelo no reside únicamente en reproducir la realidad, sino en anticipar estados futuros y optimizar decisiones.

En el contexto urbano, [(Wolf et al., 2022)](https://doi.org/10.1038/s41598-022-20178-8) desarrollaron un prototipo de gemelo digital para apoyar la gestión multiagencia de incidentes. El sistema integró información geoespacial, posición de respondedores, tráfico, clima, incidentes y rutas dentro de una plataforma común. El trabajo puso de manifiesto uno de los principales problemas de los actuales sistemas de emergencia: la existencia de fuentes heterogéneas y plataformas independientes que dificultan obtener una representación operacional integrada. Los autores plantean, además, que el sistema debe mantener ciclos de retroalimentación mediante los cuales las nuevas observaciones actualicen continuamente el estado digital.

[(Seong et al., 2025)](https://doi.org/10.1007/s43762-025-00212-x) extendieron este enfoque mediante FireCom, un Digital Twin urbano para monitorizar incendios y predecir propagación de humo en Austin, Texas. La plataforma integró incidentes, información meteorológica, sensores ambientales, infraestructura tridimensional y datos demográficos. El trabajo es relevante porque demuestra la factibilidad de fusionar fuentes con diferente resolución espacial y temporal dentro de una arquitectura de emergencia y utilizar posteriormente la representación integrada para realizar predicciones.

En el ámbito vehicular, [(Zia et al., 2026)](https://doi.org/10.1080/17445760.2024.2398082) muestran que la comunicación y priorización de información entre Digital Twins adquiere especial importancia para vehículos de emergencia, debido a los requisitos estrictos de latencia. Su propuesta de comunicación inter-twin prioriza ambulancias, policía y bomberos frente a vehículos convencionales, proporcionando una base conceptual para redes de Digital Twins en las que determinadas entidades requieren actualizaciones y decisiones con mayor urgencia.

Estas arquitecturas se conservan como antecedentes de integración y comunicación, no como una enumeración de funciones del sistema estudiado. El alcance aquí es histórico y de simulación: no comprende sensores en tiempo real, control semafórico, pronóstico de humo, tráfico o clima observado, ni comunicación entre vehículos reales.

### <a name="_xph1fhrdpqog"></a>**2.5. Aplicaciones específicas de Digital Twins al EMS**
Los trabajos específicamente orientados al transporte médico de emergencia han comenzado a mostrar el potencial operativo del paradigma. [(Roy et al., 2024)](https://doi.org/10.1145/3681772.3698213) utilizaron un entorno de Digital Twin de un corredor urbano para evaluar estrategias de Emergency Vehicle Preemption. A diferencia de los mecanismos convencionales que activan la prioridad semafórica cuando el vehículo se aproxima a una intersección, su estrategia Dynamic Preemption utiliza flujos de datos en tiempo real para anticipar la llegada del vehículo. La evaluación se realizó en un corredor simulado con intersecciones semaforizadas; sus resultados corresponden a preempción vehicular, no a la política de despacho estudiada aquí.

Otra línea aborda la sincronización entre la ambulancia física y su representación virtual. [(Al-Shareeda et al., 2025)](https://doi.org/10.1109/MENACOMM62946.2025.10910975) identificaron que la transmisión y procesamiento de datos introducen retrasos que pueden generar diferencias entre la ubicación real del vehículo y la representada por el Digital Twin. Mediante modelos SVR y redes neuronales profundas para anticipar la siguiente posición, los autores reportaron reducciones aproximadas del 88–93% en el desfase de sincronización. Este antecedente es relevante para una eventual aplicación conectada a vehículos físicos. En el presente trabajo, las posiciones pertenecen al escenario simulado y no se realiza seguimiento GPS.

La selección conjunta de hospital y ruta representa un problema distinto del despacho zonal aquí analizado. El estado de la red y la capacidad del destino pueden modificar la alternativa de transporte, pero el dataset seleccionado no identifica destinos y disponibilidad hospitalaria suficientes para evaluar ese proceso. Por ello, la gestión hospitalaria no forma parte del alcance.

A nivel organizacional, [(Penverne et al., 2024)](https://doi.org/10.1038/s41746-024-01392-2) aplicaron un Digital Twin basado en simulación para evaluar la organización de centros franceses de comunicación de emergencias. Al comparar la estructura territorial convencional con configuraciones en las que varios centros podían compartir llamadas, los escenarios de descompartimentalización incrementaron entre 17% y 21% la calidad del servicio medida mediante la proporción de llamadas respondidas dentro de 30 segundos. Este trabajo aporta evidencia de que un Digital Twin permite evaluar modificaciones organizacionales complejas sin intervenir directamente sobre un sistema de emergencia operativo. Los autores alimentan el modelo con datos reales sin sincronización en tiempo real, modalidad que sirve de antecedente al enfoque histórico de este artículo.

Finalmente, [(Li et al., 2025)](https://doi.org/10.2196/71777) sintetizan el potencial de los Digital Twins en las fases prehospitalaria, intrahospitalaria y de recuperación. Para la atención prehospitalaria, destacan específicamente la optimización de la asignación de recursos, la anticipación de variaciones de demanda y la capacidad de reducir retrasos mediante intercambio de información en tiempo real. Al mismo tiempo, señalan desafíos de resolución de datos, heterogeneidad biológica y consideraciones éticas. Su perspectiva es más amplia que la evaluación de despacho y relocalización de este estudio.
### <a name="_z9ymydm0yot"></a>**2.6. Síntesis crítica y vacío de conocimiento**
La revisión de los antecedentes permite identificar cuatro líneas de investigación que han evolucionado en paralelo. La primera demuestra la existencia de desigualdades socioeconómicas y territoriales en el acceso temporal a los EMS. La segunda desarrolla modelos de aprendizaje automático capaces de predecir la demanda de emergencias en diferentes escalas espacio-temporales. La tercera utiliza investigación de operaciones y simulación para optimizar el posicionamiento y relocalización de ambulancias. Finalmente, una cuarta línea aplica Digital Twins al transporte inteligente, respuesta ante incidentes y atención de emergencias.

Sin embargo, estas cuatro líneas no responden por sí solas a la pregunta de si una mejora predictiva produce una mejora del despacho en un escenario determinado. Los estudios de equidad describen desigualdades existentes; los modelos predictivos anticipan demanda; los modelos de relocalización evalúan tiempos, cobertura o carga de trabajo; y los Digital Twins integran información y permiten explorar alternativas. Su articulación exige distinguir calidad del pronóstico, desempeño simulado y distribución territorial de los resultados.

En consecuencia, el vacío de conocimiento que aborda este estudio no reside en la inexistencia de Digital Twins para emergencias ni en la ausencia de modelos para relocalizar ambulancias. Se concreta en evaluar, para el caso histórico seleccionado, cómo se relaciona la predicción horaria de demanda con el desempeño de una política de despacho y relocalización, bajo los mismos incidentes y recursos. Esta delimitación sustenta un EMS Digital Twin basado en simulación que compara respuesta, cobertura y diferencias territoriales, sin pretender reproducir toda la red operativa ni demostrar efectos socioeconómicos o clínicos.

### <a name="_ynk2fx40lv6z"></a>**2.7. Aprendizaje por refuerzo para el despacho y la relocalización inteligente**
Una línea más reciente de investigación está reemplazando las reglas fijas de despacho por políticas que el propio sistema aprende. [(Liu et al., 2020)](https://doi.org/10.1145/3397536.3422204) plantearon el despacho de ambulancias como un proceso de decisión de Markov multiagente y propusieron un método llamado MAQR, que aprende qué ambulancia conviene asignar a cada llamada según el estado cambiante del sistema. En escenarios donde la demanda varía rápidamente, este enfoque superó a los protocolos tradicionales. Su interés conceptual es representar consecuencias secuenciales de las decisiones. En este artículo se conserva como enfoque relacionado: el sistema utiliza pronóstico supervisado y reglas heurísticas, no entrenamiento de agentes por refuerzo ni una recompensa de equidad.
## <a name="_6ipt8cber7nc"></a>**3. Marco teórico**
### <a name="_ggpx8w969zpk"></a>**3.1. Digital Twin como modelo de simulación basado en datos históricos**
En esta investigación, un Digital Twin se conceptualiza como una representación computacional dinámica de un sistema EMS por zonas que utiliza datos históricos para simular, predecir demanda y comparar decisiones de asignación. Se adopta la modalidad basada en simulación, no la de un sistema ciberfísico sincronizado en tiempo real. Por tanto, su valor no se limita a una representación cartográfica estática, sino que reside en relacionar datos, evolución de estados y evaluación de políticas.

Conceptualmente, el funcionamiento del gemelo puede representarse mediante la siguiente secuencia:

**Datos históricos → estado del escenario → predicción de demanda → decisiones de despacho → evolución simulada → evaluación.**


En un Digital Twin operacional conectado, las observaciones del mundo físico actualizan el estado del gemelo y las acciones pueden modificar el servicio real. En este estudio, los registros históricos alimentan el escenario y las acciones modifican exclusivamente estados simulados. No se requiere seguimiento GPS ni se ejecutan decisiones sobre una flota real. Las arquitecturas planteadas por [(Chen et al., 2024)](https://doi.org/10.1109/COMST.2023.3308717), [(Petri et al., 2023)](https://doi.org/10.1016/j.jii.2023.100445) y [(Wolf et al., 2022)](https://doi.org/10.1038/s41598-022-20178-8) proporcionan fundamentos para esta interpretación de integración entre datos, modelos y decisiones.

Aplicado a EMS, el sistema físico está constituido por ambulancias, bases, hospitales, llamadas de emergencia y red de transporte. Su estado operacional se modifica constantemente debido a nuevas llamadas, finalización de servicios, movimientos de vehículos, congestión, meteorología y cambios en la disponibilidad hospitalaria. En consecuencia, un EMS puede representarse como un sistema dinámico estocástico espacio-temporal. El modelo de este estudio abstrae la demanda y disponibilidad por zonas; los tiempos de viaje y liberación y la configuración de flota no identificables en los registros se documentan como supuestos, sin incorporar información hospitalaria, meteorológica o de tráfico en tiempo real.
### <a name="_s3kp4hg9yjp3"></a>**3.2. EMS como sistema de colas, cobertura y asignación espacial**
Desde la teoría de sistemas, el desempeño de los EMS emerge de la interacción entre procesos de llegada de demanda y recursos con capacidad limitada. Las llamadas aparecen de forma estocástica; una ambulancia puede encontrarse disponible, desplazándose, atendiendo a un paciente, transportándolo o recuperando disponibilidad. Una emergencia que ocurre mientras los recursos cercanos están ocupados debe ser atendida desde posiciones más distantes, incrementando el tiempo de respuesta y modificando simultáneamente la cobertura restante.

Por tanto, minimizar individualmente la distancia entre una ambulancia y una llamada no garantiza una solución globalmente eficiente. Despachar la ambulancia más cercana puede dejar una región sin cobertura y producir mayores tiempos de respuesta en llamadas posteriores. La decisión correcta depende del estado completo de la flota y de la distribución probable de demanda futura.

La relocalización dinámica introduce precisamente este componente anticipatorio. En lugar de esperar que ocurra la siguiente emergencia, los recursos disponibles pueden desplazarse preventivamente hacia zonas con mayor probabilidad de demanda o hacia sectores cuya cobertura se ha deteriorado. La revisión de [(Becker et al., 2023)](https://doi.org/10.1136/bmjopen-2023-073394) y los modelos recientes de optimización confirman que la ubicación de hospitales, estimaciones de demanda, disponibilidad y características geográficas constituyen variables fundamentales para estas decisiones.

En la simulación, el tiempo de respuesta se calcula como llegada a escena menos creación de la llamada. Los intervalos históricos sirven para caracterización y calibración, no se suman completos a nuevas esperas. La flota, sus posiciones y las reglas de liberación son parámetros documentados; los incidentes sin llegada al cierre se conservan para evitar evaluar únicamente los casos atendidos.

### <a name="_nxyfuz7l05jr"></a>**3.3. Predicción espacio-temporal y despacho predictivo**
Sea D(z,t,h) la demanda esperada de llamadas EMS en una zona geográfica z durante un horizonte futuro h. El problema predictivo puede expresarse conceptualmente como:

`D(z,t,h) = f(D_hist(z,<t), Cal(t), z)`

Donde:

- D(z,t,h): conteo esperado en la zona z durante [t,t+h).
- D_hist(z,<t): conteos anteriores al instante de emisión, incluidos rezagos de 1, 24 y 168 horas.
- Cal(t): variables de calendario, como hora y día de la semana.
- z: borough al que corresponde el pronóstico.
- h: horizonte primario de 60 minutos.
- f: modelo predictivo; se compara una regresión de Poisson con persistencia semanal y promedio histórico por zona, día de semana y hora.

Esta predicción constituye la transición desde el despacho reactivo hacia el despacho predictivo. En un esquema convencional, la acción comienza después de recibida una llamada. En el modelo predictivo, el sistema estima el volumen de llamadas durante la siguiente hora y utiliza dichas estimaciones para actualizar preventivamente la distribución de ambulancias.

Los resultados recientes sobre forecasting EMS respaldan evaluar modelos capaces de capturar relaciones espacio-temporales, pero no determinan un ganador para otro contexto. El estudio no incorpora tráfico, clima, eventos extraordinarios ni características socioeconómicas como entradas sin fuentes compatibles. En el Digital Twin propuesto, el pronóstico no representa un objetivo final, sino una entrada del módulo de decisión.

El diseño distingue entrenamiento del 1 de abril al 15 de mayo de 2026, validación del 16 al 31 de mayo y prueba del 1 al 30 de junio. Las primeras 168 horas se reservan para formar rezagos; las transformaciones se ajustan con entrenamiento y las decisiones del modelo se cierran con validación. MAE, RMSE y WAPE se calculan sobre las mismas celdas borough-hora válidas. La exactitud predictiva se evalúa por separado del desempeño simulado, sin utilizar información futura al despachar.

### <a name="_g1imjrtjlzk"></a>**3.4. Optimización dinámica de recursos**
Una vez estimada la demanda futura, debe determinarse la posición de la flota. En la literatura de optimización, puede definirse una variable binaria:

xij, t = 1, si la ambulancia i es asignada o relocalizada a la zona j en t

xij, t = 0, si la ambulancia i no es asignada ni relocalizada a j en t

Donde:

- i: ambulancia.
- j: zona, estación o punto candidato de relocalización.
- t: periodo de decisión.
- xij, t: decisión tomada por el optimizador.

Esta variable puede utilizarse dentro de un modelo de programación lineal entera mixta (MILP), con una función multiobjetivo ilustrativa del tipo:

`min Z = α Tresp + β Deq + γ Creloc + δ U`

Donde:

- Z: valor total que debe minimizar el modelo.
- Tresp: tiempo medio esperado de respuesta EMS.
- Deq: medida de disparidad o inequidad entre grupos socioeconómicos.
- Creloc: costo asociado con la relocalización de ambulancias.
- U: demanda esperada no cubierta o insuficientemente cubierta.
- α,β,γ,δ: pesos asignados a cada objetivo.

Esta formulación se alinea con la evidencia de [(Gago-Carro et al., 2024)](https://doi.org/10.1016/j.eswa.2024.123665), quienes demuestran que la equidad puede incorporarse explícitamente dentro de modelos de asignación de ambulancias. La formulación se incluye como antecedente conceptual, no como el algoritmo implementado en este sistema. El presente marco utiliza una puntuación heurística de tiempo estimado de llegada, demanda de la zona de origen y cobertura residual, junto con reglas periódicas de relocalización. No resuelve un MILP ni utiliza quintiles socioeconómicos; los pesos y desempates quedan fijados antes de la prueba.

Otras formulaciones de la literatura incorporan un criterio clínico: la supervivencia esperada. [(Erkut et al., 2008)](https://doi.org/10.1002/nav.20267) mostraron que, si en los modelos de localización se incorpora una función de supervivencia que disminuye de forma monótona conforme aumenta el tiempo de respuesta (calibrada con datos de paro cardíaco), las soluciones quedan mejor alineadas con el resultado clínico real que si solo se maximiza la cobertura binaria. De hecho, dos configuraciones con la misma cobertura pueden diferir bastante en el número esperado de personas que sobreviven. Este antecedente permite distinguir cobertura temporal y desenlace clínico. El presente estudio no estima supervivencia ni incluye una función S(x), porque los registros utilizados no permiten evaluar ese efecto.

Ahora bien, cuando el espacio de estados es demasiado grande para hacer una optimización exacta en cada periodo, otra opción es que las políticas de despacho se aprendan mediante aprendizaje por refuerzo. En ese caso, el estado del gemelo digital (posiciones, ocupación y demanda pronosticada) funciona como la observación; las asignaciones y relocalizaciones constituyen el espacio de acciones; y una función de recompensa orienta el aprendizaje [(Liu et al., 2020)](https://doi.org/10.1145/3397536.3422204).

Esta alternativa tampoco forma parte del método evaluado. La comparación principal contrasta políticas completas; atribuir una diferencia exclusivamente al pronóstico o a la relocalización requiere experimentos de ablación.

### <a name="_vhyke0ha9y1q"></a>**3.5. Simulación temporal como motor experimental del Digital Twin**
Los EMS están formados por eventos que modifican su estado en instantes determinados: aparición de una llamada, asignación de una unidad, salida de una base, llegada a escena, inicio del transporte, ingreso hospitalario y recuperación de disponibilidad. Debido a esta naturaleza, la simulación de eventos discretos constituye un antecedente apropiado para representar su comportamiento. El motor de este estudio procesa las transiciones en pasos fijos de un minuto, en lugar de avanzar directamente al siguiente evento; esa resolución debe considerarse al interpretar duraciones y umbrales.

En este paradigma, el Digital Twin puede ejecutar escenarios contrafactuales manteniendo constantes las mismas llamadas históricas mientras modifica la política de despacho y relocalización, conservando flota inicial y condiciones exógenas equivalentes. Esta capacidad permite comparar, bajo condiciones equivalentes:

**Escenario A:** despacho reactivo por menor tiempo estimado de llegada entre unidades disponibles.

**Escenario B:** despacho asistido por pronósticos y relocalización heurística dentro del Digital Twin.

El valor de este enfoque ha sido demostrado por [(Penverne et al., 2024)](https://doi.org/10.1038/s41746-024-01392-2), quienes utilizaron un gemelo basado en simulación para evaluar configuraciones organizacionales de centros de emergencia sin alterar previamente el sistema real, y por [(Essus et al., 2024)](https://doi.org/10.1016/j.cie.2023.109823), quienes integraron optimización en tiempo real con simulación discreta.

La simulación también permite someter el sistema a perturbaciones, como incrementos de demanda, cambios en el número de ambulancias y variaciones de los tiempos de viaje y ocupación. Estas perturbaciones se declaran como escenarios de sensibilidad, no como reconstrucciones observadas de tormentas o eventos masivos.

Los experimentos utilizan variaciones aleatorias emparejadas por incidente o componente; compartir una semilla no basta si cada política consume números de forma distinta. El diseño contempla inicialmente 30 pares, ajustables por precisión en validación, con intervalos del 95 % que respeten el emparejamiento y la dependencia temporal. La diferencia primaria es respuesta media predictiva menos reactiva por par. Se fijan calentamiento, medición y vaciado, y se reportan llamadas pendientes junto a las medias de los incidentes con llegada.

### <a name="_bld0x0b98dpq"></a>**3.6. Equidad espacial como dimensión de desempeño**
Una dimensión relevante del presente estudio es que la eficiencia global no se considera suficiente. La equidad espacial motiva examinar cómo se distribuye la respuesta oportuna entre territorios. Su operacionalización aquí es descriptiva por borough, ya que no se dispone de quintiles socioeconómicos ni se identifican causas de desigualdad.

Sea:

`P_z = P(T_respuesta < τ | zona = z)`

Donde:

- P_z: probabilidad de respuesta antes del umbral en la zona z.
- T_respuesta: tiempo entre creación de la llamada y llegada a escena.
- τ: umbral analítico de ocho minutos, no un estándar clínico universal.
- z: borough analizado, no quintil socioeconómico.

La tasa histórica utiliza incidentes con respuesta válida. La tasa simulada utiliza llamadas con al menos 480 segundos de seguimiento; las que no llegan antes del umbral cuentan como incumplidas. Estas tasas se presentan por separado porque sus denominadores difieren.

Una medida complementaria compara las medias zonales de respuesta:

`Brecha = max_z(media_z) - min_z(media_z)`

`Razón de disparidad = max_z(media_z) / min_z(media_z)`

Una razón próxima a 1 indica medias similares, sin demostrar por sí sola equidad. No se calcula con mínimo cero ni con menos de dos zonas válidas; cada indicador se acompaña de tamaño de muestra y composición de casos.

El fundamento empírico para incorporar esta dimensión está dado por la evidencia de [(Hsia et al., 2018)](https://doi.org/10.1001/jamanetworkopen.2018.5202); [(Verma et al., 2023)](https://doi.org/10.1016/j.focus.2023.100129), quienes identificaron asociaciones significativas entre nivel socioeconómico y tiempos EMS. Asimismo, Gago-Carro et al. (2024) demuestran desde la investigación de operaciones que una función orientada a equidad puede mejorar sustancialmente la atención de territorios históricamente desfavorecidos.

Por esta razón, el tiempo medio de respuesta debe complementarse con análisis estratificados. Una intervención puede reducir el promedio urbano y, simultáneamente, aumentar la desigualdad si las ganancias se concentran en sectores que ya disponían de alta cobertura. El Digital Twin propuesto evalúa, por tanto, **eficiencia absoluta** como **distribución territorial del desempeño simulado**, sin anticipar mejoras.
### <a name="_xuwhwb3wi9bw"></a>**3.7. Modelo conceptual integrador**
A partir de los fundamentos anteriores, el marco teórico del estudio puede sintetizarse mediante la siguiente secuencia analítica y de simulación:

**Datos históricos locales → limpieza y cohortes → pronóstico horario → despacho y relocalización → evolución simulada → indicadores globales y territoriales.**


El Digital Twin funciona como la infraestructura que conecta todas estas capas mediante actualizaciones del estado simulado. Los datos históricos alimentan las llegadas; el modelo predictivo anticipa demanda; las reglas de decisión proponen redistribuciones; el simulador estima sus consecuencias; y las métricas de desempeño evalúan eficiencia y diferencias territoriales.

De esta manera, la contribución conceptual del estudio no consiste simplemente en utilizar inteligencia artificial, optimización o simulación por separado, sino en integrarlas dentro de un **sistema de apoyo al análisis de decisiones EMS basado en simulación**, en el cual la distribución futura de la demanda modifica dinámicamente la posición de los recursos y las decisiones son evaluadas no solo por su efecto en el tiempo promedio, sino también por cómo se distribuye el desempeño entre zonas. No se presupone una reducción ni se atribuyen efectos sobre desigualdad socioeconómica.

La fuente es [FDNY, EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj), con 405 998 registros originales de abril a junio de 2026. La API se utiliza para adquisición; la limpieza y los experimentos trabajan sobre una copia local versionada. La cohorte principal excluye transferencias, standby y eventos especiales conocidos, conservando indicadores desconocidos por separado. Los faltantes de respuesta no eliminan automáticamente una llamada de la cohorte de demanda. Los registros no reconstruyen posiciones exactas, identidad y disponibilidad de la flota ni destinos hospitalarios: esos límites se mantienen explícitos en el escenario. La vista 3D representa estados del modelo y no seguimiento real.

### <a name="_vsid4knaidjg"></a>**3.8. Robustez, limitaciones y transferibilidad de la política dinámica**
Una arquitectura de decisión para servicios de emergencias médicas requiere examinar la sensibilidad de sus recomendaciones a las condiciones del escenario. En ese sentido, la literatura ofrece un antecedente de cumplimiento parcial evaluado mediante simulación: [(Lam et al., 2015)](https://doi.org/10.1016/j.ajem.2014.10.044) observaron que, cumpliendo apenas el 60% de los desplazamientos recomendados, los tiempos de respuesta y la cobertura seguían siendo mejores que con una política estática. Este resultado corresponde a la simulación de ese estudio, no a un umbral universal de cumplimiento ni a evidencia de funcionamiento del presente sistema en un servicio real.

Además, la revisión sistemática de [(Soltani et al., 2026)](https://doi.org/10.1108/IJES-01-2025-0002) advierte que muchos estudios de optimización en emergencias se limitan a contextos muy específicos y condiciones estables, lo que dificulta generalizar sus resultados. Por eso, la fase de validación del gemelo digital debería contemplar escenarios de sensibilidad frente a demanda, flota, tiempos de viaje y duración de ocupación. Estos cambios se expresan como supuestos controlados, sin requerir GPS ni datos de tráfico en tiempo real. Así, la política de despacho predictivo no se evaluaría únicamente por su desempeño esperado, sino también por su capacidad de resistir perturbaciones realistas.

La evaluación combina análisis retrospectivo y experimentación computacional; no incluye intervención en ambulancias reales. La calibración contrasta magnitudes no impuestas directamente como entradas y utiliza entrenamiento y validación antes de la prueba. La falta de información completa de flota limita la identificación del escenario: un resultado que cambie sustancialmente con sus supuestos se interpreta como dependiente de ellos. Las conclusiones no demuestran mejoras reales en Nueva York o Trujillo, ni beneficios clínicos; tres meses tampoco establecen generalización anual.

La evaluación por personas constituye un componente complementario y utiliza instrumentos específicos. La [V de Aiken (1985)](https://doi.org/10.1177/0013164485451012) aporta evidencia de contenido mediante expertos; el [alfa de Cronbach (1951)](https://doi.org/10.1007/BF02310555) examina consistencia interna por dimensión de una escala Likert de utilidad percibida; y [KR-20, Kuder y Richardson (1937)](https://doi.org/10.1007/BF02288391) corresponde a un test de interpretación con ítems correctos e incorrectos. Los instrumentos requieren participantes pertinentes, reglas de puntuación, consentimiento y tratamiento de faltantes e incertidumbre. Estos coeficientes no se calculan sobre las filas EMS ni demuestran exactitud predictiva o beneficio del despacho. Alfa y KR-20 para los mismos ítems dicotómicos no son validaciones independientes.

La transferibilidad se entiende como posibilidad de adaptar el procedimiento a otros datos y parámetros, no como traslado automático de resultados. La aplicación operativa requiere validación contextual y prospectiva, localización y disponibilidad actualizadas de recursos, integración institucional y supervisión humana, aspectos fuera del alcance del artículo.

## <a name="metodologia"></a>**4. Metodología**

### <a name="metodologia-diseno"></a>**4.1. Diseño y ámbito del estudio**

Se desarrolla un estudio cuantitativo aplicado que combina análisis retrospectivo de registros EMS de Nueva York y experimentación computacional por borough. Se compara una política asistida por pronósticos y relocalización con una política reactiva, bajo condiciones simuladas equivalentes. Las unidades de análisis son el incidente para los registros históricos, la celda borough-hora para el pronóstico y el par de réplicas para la comparación experimental. La evaluación con expertos y usuarios constituye un componente complementario. No se interviene en un servicio real.

El diseño adapta la evaluación temporal de [Monks et al. (2023)](https://doi.org/10.1186/s12911-023-02218-z), la conexión entre pronóstico y simulación de [Matteson et al. (2011)](https://doi.org/10.1214/10-AOAS442) y la comparación de escenarios de [Lam et al. (2015)](https://doi.org/10.1016/j.ajem.2014.10.044) y [Penverne et al. (2024)](https://doi.org/10.1038/s41746-024-01392-2). La exactitud predictiva, el desempeño simulado y la evaluación instrumental se analizan por separado.

### <a name="metodologia-datos"></a>**4.2. Fuente de datos, población y selección de registros**

#### Fuente de datos

Se utiliza [EMS Incident Dispatch Data de FDNY](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj), adquirido mediante la API de Socrata y almacenado localmente. La copia corresponde a la extracción del 9 de septiembre de 2026. Se adopta la convención de hora local de Nueva York, conservando las fechas originales.

#### Población, muestra y muestreo

La población accesible está constituida por los 405 998 incidentes publicados con fecha de creación entre el 1 de abril y el 30 de junio de 2026, disponibles en dicha extracción. La unidad de origen es el incidente, no el paciente ni el recorrido de una ambulancia. Se realiza un análisis censal de la ventana seleccionada, sin extraer una muestra aleatoria de filas ni calcular un tamaño muestral para los incidentes. La selección temporal es intencional y no garantiza representatividad anual. El conjunto analítico final queda definido por los criterios de calidad y elegibilidad de cada cohorte.

#### Criterios de selección y procesamiento de datos

La preparación verifica tipos, faltantes, identificadores, duplicados, cobertura temporal, categorías y coherencia de duraciones. Se eliminan copias exactas redundantes y se separan identificadores conflictivos sin elegir arbitrariamente una versión. Los originales permanecen inalterados y se registran los motivos de exclusión.

| Cohorte | Criterio principal | Uso |
|---|---|---|
| Aceptados | Identificador y fecha válidos, dentro de la ventana y sin conflicto | Descripción y reconciliación |
| Demanda principal | Aceptados con transferencia, standby y evento especial explícitamente negativos | Llegadas y conteos |
| Demanda zonal | Demanda principal con borough verificado | Pronóstico por zona |
| Respuesta o despacho | Demanda principal con bandera válida y fechas y duración coherentes para el intervalo correspondiente | Caracterización y calibración |

Las banderas desconocidas se contabilizan separadamente. Una respuesta inválida no elimina el incidente de la demanda; tampoco se excluyen automáticamente esperas o reaperturas. Las zonas desconocidas no se distribuyen artificialmente. No se imputan tiempos objetivo ni se eliminan valores extremos temporalmente coherentes. Se informa el tamaño final por cohorte, mes y territorio. Las reglas detalladas y la trazabilidad de extracción se mantienen en la documentación técnica complementaria del estudio.

### <a name="metodologia-prediccion"></a>**4.3. Desarrollo y validación de los modelos predictivos**

La variable objetivo es el número de llamadas por borough durante la siguiente hora. Se construyen variables de calendario, zona, rezagos de 1, 24 y 168 horas y medias móviles de 24 y 168 horas, exclusivamente con intervalos anteriores al pronóstico. Las primeras 168 horas se reservan para formar características. Solo se completan conteos con cero cuando la cobertura de fuente es verificable; los periodos sin cobertura permanecen faltantes.

| Partición | Periodo de 2026 | Finalidad |
|---|---|---|
| Entrenamiento | 1 de abril–15 de mayo | Ajuste de transformaciones y modelos |
| Validación | 16–31 de mayo | Selección del modelo y configuración |
| Prueba | 1–30 de junio | Evaluación temporal con parámetros congelados |

Se comparan persistencia semanal, promedio histórico por borough, día y hora, y regresión de Poisson con enlace logarítmico. Las transformaciones se ajustan con entrenamiento y cualquier búsqueda de características o regularización se limita a validación. Se selecciona por MAE global, favoreciendo simplicidad en empate. En prueba se emiten pronósticos horarios sucesivos: pueden utilizar conteos de horas ya terminadas, nunca información futura. Se asume disponibilidad del conteo al cierre de cada hora, sin atribuir funcionamiento en tiempo real a la API pública.

Para \(n\) celdas válidas, conteos observados \(y_i\) y pronósticos \(\hat{y}_i\), se calculan:

$$
\mathrm{MAE}=\frac{1}{n}\sum_{i=1}^{n}|y_i-\hat{y}_i|,
\qquad
\mathrm{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat{y}_i)^2},
\qquad
\mathrm{WAPE}=100\frac{\sum_{i=1}^{n}|y_i-\hat{y}_i|}{\sum_{i=1}^{n}y_i}.
$$

Se reportan métricas globales y zonales sobre las mismas celdas; WAPE no se calcula con total observado cero. Las diferencias de MAE se acompañan de intervalos del 95 % mediante 2 000 remuestreos de bloques temporales, compartidos entre zonas y modelos. La longitud de bloque se fija con validación para conservar la dependencia temporal.

### <a name="metodologia-escenario"></a>**4.4. Modelo de simulación: verificación y validación**

El simulador incorpora llegadas históricas elegibles y representa asignación, desplazamiento, ocupación y liberación de recursos en pasos de un minuto. Genera sus propios tiempos de respuesta; los históricos se reservan para caracterización y contraste. La geografía externa se versiona y las posiciones representativas no se presentan como coordenadas observadas ni GPS. La flota, los tiempos de viaje y la ocupación no identificables en los datos se declaran como supuestos. El cierre de un incidente no equivale automáticamente a liberar una unidad.

Siguiendo a [Sargent (2013)](https://doi.org/10.1057/jos.2012.20), la verificación comprueba conservación de recursos, asignaciones compatibles, secuencias temporales, colas y contabilización de incidentes. La calibración ajusta componentes con entrenamiento y contrasta respuesta, mediana y P90 por zona y franja en validación, sobre magnitudes comparables no impuestas directamente como entradas.

Antes de prueba se fijan flota, geografía, tiempos, liberación, prioridades, desempates, calentamiento, corte final y tolerancias de calibración. La política reactiva es un comparador experimental, no una reconstrucción comprobada del despacho FDNY. Si el contraste no respalda la plausibilidad del escenario, la comparación se interpreta como exploratoria.

### <a name="metodologia-experimentos"></a>**4.5. Escenarios experimentales y análisis estadístico**

#### Escenarios y réplicas

Se comparan dos políticas con las mismas reglas de elegibilidad y prioridad: A, reactiva, asigna la unidad disponible con menor tiempo estimado de llegada; B, asistida, combina tiempo de llegada, demanda prevista en origen y cobertura residual mediante una puntuación heurística y relocalización periódica. Sus pesos y restricciones se fijan con validación. Relocalizar consume tiempo y modifica la disponibilidad. La comparación evalúa el paquete completo; atribuir efectos a componentes individuales requiere ablación.

Cada par de réplicas comparte incidentes de junio, estado inicial y variaciones exógenas preasignadas por incidente o componente; entre pares se emplean flujos independientes. Se parte de 30 pares y se fija el número definitivo con la variabilidad de validación y una precisión objetivo, antes de prueba. El calentamiento utiliza historia anterior a junio y ambas políticas comparten reglas de vaciado y corte, conservando solicitudes pendientes.

#### Variables de resultado y análisis estadístico

La variable primaria es la diferencia de respuesta media entre políticas. Para cada incidente con llegada, se calcula el tiempo de respuesta; la diferencia por réplica y su promedio sobre \(m\) pares válidos son:

$$
R_i=t_{\mathrm{llegada},i}-t_{\mathrm{llamada},i},
\qquad
D_r=\overline{R}_{B,r}-\overline{R}_{A,r},
\qquad
\overline{D}=\frac{1}{m}\sum_{r=1}^{m}D_r.
$$

Valores negativos favorecen B en respuesta media. Se obtiene un intervalo del 95 % mediante 2 000 remuestreos de pares completos y percentiles 2,5 y 97,5. Esta incertidumbre es condicional a las llegadas históricas y supuestos; incidentes o días contiguos no constituyen réplicas independientes.

| Indicador | Definición |
|---|---|
| Respuesta media, mediana y P90 | Llegada menos llamada, en minutos, entre casos con llegada; se informa n |
| Cobertura inferior a ocho minutos | Entre llamadas con al menos 480 segundos de seguimiento, proporción con llegada antes de ese umbral |
| Fracción sin llegada | Llamadas sin llegada al corte / llamadas admitidas |
| Utilización | Minutos-unidad ocupados / minutos-unidad programados |
| Brecha territorial | Máxima menos mínima media zonal de respuesta |
| Razón de disparidad | Máxima / mínima media zonal; no disponible con mínimo cero o menos de dos zonas válidas |

Se reportan denominadores y faltantes; ocho minutos es un umbral analítico, no una recomendación clínica. La cobertura histórica tiene una cohorte diferente y se describe separadamente. Como la respuesta media condicionada a llegada puede ocultar llamadas sin atender, se interpreta junto con cobertura y pendientes, y se complementa con casos completados por ambas políticas y sensibilidad al vaciado.

#### Análisis de sensibilidad

El análisis de sensibilidad considera flota, tiempos de viaje y ocupación dentro de límites justificados antes de prueba, manteniendo condiciones emparejadas. Se examinan magnitud, dirección e incertidumbre, incluyendo cambios de signo. Los indicadores secundarios son exploratorios. La agregación territorial, los faltantes, los supuestos de recursos y la ventana trimestral limitan la generalización; las diferencias simuladas no demuestran mejoras operativas o clínicas.

### <a name="metodologia-instrumentos"></a>**4.6. Participantes e instrumentos de evaluación**

#### Población, muestra y muestreo de participantes

La población de interés comprende adultos con formación o experiencia en gestión de emergencias, salud, simulación, investigación de operaciones o análisis de datos, capaces de interpretar los escenarios del sistema. Se distinguen un panel de expertos, seleccionado mediante muestreo no probabilístico intencional según experiencia pertinente, y un grupo de usuarios para la aplicación de instrumentos. La institución o ámbito de reclutamiento delimita la población accesible y debe especificarse antes de la convocatoria. Para usuarios, se documenta el procedimiento efectivo; si es por conveniencia, no se presume representatividad.

El tamaño del panel se justifica según la precisión de V de Aiken y la diversidad de experiencia requerida. La muestra de usuarios se determina según precisión de los coeficientes, número de ítems y factibilidad. Ambos tamaños se fijan antes de la aplicación y se informan por separado; los 405 998 incidentes no constituyen la muestra para evaluar instrumentos.

#### Instrumentos, procedimiento de aplicación y análisis

La recolección de información utiliza tres instrumentos: una ficha de juicio de expertos, un cuestionario de utilidad percibida y una prueba de interpretación de resultados. El cuestionario recoge valoraciones subjetivas mediante encuesta, mientras que la prueba evalúa respuestas a tareas con una clave de corrección. Los coeficientes de Aiken, Cronbach y KR-20 se calculan a partir de las respuestas; no constituyen instrumentos de recolección.

| Instrumento | Quién responde | Contenido y formato |
|---|---|---|
| Ficha de juicio de expertos | Panel de expertos | Valoración de claridad, pertinencia y relevancia de cada ítem del cuestionario y de la prueba, de 1 a 4, con observaciones cualitativas |
| Cuestionario de utilidad percibida | Usuarios después de realizar tareas en el sistema | Afirmaciones sobre la utilidad del sistema para analizar demanda y comparar escenarios, con respuestas Likert de 1 (totalmente en desacuerdo) a 5 (totalmente de acuerdo) |
| Prueba de interpretación de resultados | Usuarios ante escenarios e indicadores del sistema | Preguntas sobre demanda, comparación de políticas, tiempos, cobertura e incertidumbre, calificadas como 1 (correcta) o 0 (incorrecta) |

**Revisión de contenido y prueba piloto.** Los ítems se vinculan previamente con las dimensiones de utilidad o capacidades de interpretación que pretenden medir. Los expertos revisan ambos instrumentos, incluidos los enunciados, opciones y clave de la prueba. Para cada ítem y criterio se calcula V de [Aiken (1985)](https://doi.org/10.1177/0013164485451012), con \(n\) jueces y calificación \(r_j\):

$$
V=\frac{\sum_{j=1}^{n}(r_j-1)}{3n}.
$$

Se presentan intervalos del 95 % mediante el procedimiento score de [Penfield y Giacobbi (2004)](https://doi.org/10.1207/s15327841mpee0804_3), junto con observaciones cualitativas y criterios de revisión definidos antes de recoger valoraciones. Tras los ajustes, un piloto con participantes distintos de la aplicación principal revisa comprensión, duración y funcionamiento de las tareas. Se fija la versión definitiva antes de evaluar al grupo principal; no se agrupan respuestas de versiones diferentes.

**Aplicación a usuarios.** Cada participante recibe las mismas instrucciones y realiza una secuencia estandarizada de tareas: consultar demanda por zona, comparar las políticas reactiva y asistida e interpretar indicadores de los escenarios. Después responde individualmente el cuestionario de utilidad percibida y la prueba, con acceso a los resultados necesarios para resolverla y sin ayuda para elegir respuestas. Se registran omisiones y se utiliza una clave de corrección definida previamente. Los ítems, tareas, instrucciones y clave forman parte de la documentación del procedimiento.

**Consistencia interna.** Las respuestas al cuestionario se analizan mediante alfa de [Cronbach (1951)](https://doi.org/10.1007/BF02310555) por dimensión, mientras que las puntuaciones dicotómicas de la prueba se analizan con KR-20 de [Kuder y Richardson (1937)](https://doi.org/10.1007/BF02288391):

$$
\alpha=\frac{k}{k-1}\left(1-\frac{\sum_{i=1}^{k}s_i^2}{s_{\mathrm{total}}^2}\right),
\qquad
\mathrm{KR}_{20}=\frac{k}{k-1}\left(1-\frac{\sum_{i=1}^{k}p_i(1-p_i)}{\sigma_{\mathrm{total}}^2}\right).
$$

Aquí \(k\) es el número de ítems, \(p_i\) la proporción correcta, \(s^2\) la varianza muestral y \(\sigma_{\mathrm{total}}^2\) la varianza poblacional del puntaje total. Se utilizan casos completos por dimensión o prueba, inversiones previamente definidas e intervalos percentiles del 95 % con 2 000 remuestreos de participantes. Se informan exclusiones y remuestreos degenerados; no se calcula con menos de dos ítems, casos insuficientes o varianza total cero. Los faltantes no equivalen a respuestas incorrectas y los coeficientes negativos no se recortan.

Las valoraciones de utilidad y los aciertos de interpretación se describen por separado de los coeficientes. Aiken aporta evidencia de validez de contenido y alfa y KR-20 estiman consistencia interna; no demuestran utilidad elevada, mejora del aprendizaje, exactitud predictiva ni validez del simulador.

### <a name="metodologia-etica"></a>**4.7. Consideraciones éticas y reproducibilidad**

Los datos públicos se utilizan sin reidentificar personas y los resultados se presentan agregados. La evaluación instrumental requiere participación voluntaria, consentimiento, confidencialidad y determinación institucional de los requisitos éticos antes del reclutamiento, sin presumir aprobación. El estudio no ofrece decisiones clínicas ni despacha recursos reales; participantes peruanos no validan por sí solos la operación en Trujillo.

El procesamiento utiliza scripts Python y la aplicación intercambia artefactos versionados de datos, modelos, escenarios y resultados. La documentación técnica conserva consultas, reglas de limpieza, semillas, parámetros, versiones y verificaciones de integridad, siguiendo los componentes aplicables de STRESS [Monks et al. (2019)](https://doi.org/10.1080/17477778.2018.1442155). Los tamaños definitivos de muestras y réplicas y los valores de calibración se documentan antes de sus evaluaciones; no se presentan como resultados ya obtenidos.

## <a name="_323l0gnzir9s"></a>**Referencias**

Aiken, L. R. (1985). Three coefficients for analyzing the reliability and validity of ratings. *Educational and Psychological Measurement, 45*(1), 131–142. [DOI](https://doi.org/10.1177/0013164485451012).

Al-Shareeda, S., Celik, Y., Bilgili, B., Al-Dubai, A., & Canberk, B. (2025). Accurate AI-Driven Emergency Vehicle Location Tracking in Healthcare ITS’s Digital Twin. *2025 5th IEEE Middle East and North Africa Communications Conference (MENACOMM)*, 1–8. [DOI](https://doi.org/10.1109/MENACOMM62946.2025.10910975)

Becker, J., Kurland, L., Höglund, E., & Hugelius, K. (2023). Dynamic ambulance relocation: A scoping review. *BMJ Open*, *13*(12), e073394. [DOI](https://doi.org/10.1136/bmjopen-2023-073394)

Chen, J., Yi, C., Okegbile, S. D., Cai, J., & Shen, X. (2024). Networking Architecture and Key Supporting Technologies for Human Digital Twin in Personalized Healthcare: A Comprehensive Survey. *IEEE Communications Surveys & Tutorials*, *26*(1), 706–746. [DOI](https://doi.org/10.1109/COMST.2023.3308717)

Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests. *Psychometrika, 16*, 297–334. [DOI](https://doi.org/10.1007/BF02310555).

Erkut, E., Ingolfsson, A., & Erdoğan, G. (2008). Ambulance location for maximum survival. *Naval Research Logistics (NRL)*, *55*(1), 42–58. [DOI](https://doi.org/10.1002/nav.20267)

Essus, Y., De La Fuente, R., & Venkitasubramanian, A. (2024). Real-time optimization for relocation and dispatching of Emergency Medical Services with balanced workload and outsourced ride-hailing services. *Computers & Industrial Engineering*, *187*, 109823. [DOI](https://doi.org/10.1016/j.cie.2023.109823)

Fire Department of the City of New York (FDNY). (s. f.). *EMS Incident Dispatch Data* [Conjunto de datos]. NYC Open Data. [Dataset 76xm-jjuj](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj). Ventana de estudio: abril–junio de 2026.

Gago-Carro, I., Aldasoro, U., Ceberio, J., & Merino, M. (2024). A stochastic programming model for ambulance (re)location–allocation under equitable coverage and multi-interval response time. *Expert Systems with Applications*, *249*, 123665. [DOI](https://doi.org/10.1016/j.eswa.2024.123665)

Gendreau, M., Laporte, G., & Semet, F. (2001). A dynamic model and parallel tabu search heuristic for real-time ambulance relocation. *Parallel Computing*, *27*(12), 1641–1653. [DOI](https://doi.org/10.1016/S0167-8191%2801%2900103-X)

Hsia, R. Y., Huang, D., Mann, N. C., Colwell, C., Mercer, M. P., Dai, M., & Niedzwiecki, M. J. (2018). A US National Study of the Association Between Income and Ambulance Response Time in Cardiac Arrest. *JAMA Network Open*, *1*(7), e185202. [DOI](https://doi.org/10.1001/jamanetworkopen.2018.5202)

Jagtenberg, C. J., & Mason, A. J. (2020). Improving fairness in ambulance planning by time sharing. *European Journal of Operational Research*, *280*(3), 1095–1107. [DOI](https://doi.org/10.1016/j.ejor.2019.08.003)

Kuder, G. F., & Richardson, M. W. (1937). The theory of the estimation of test reliability. *Psychometrika, 2*, 151–160. [DOI](https://doi.org/10.1007/BF02288391).

Lam, S. S. W., Zhang, J., Zhang, Z. C., Oh, H. C., Overton, J., Ng, Y. Y., & Ong, M. E. H. (2015). Dynamic ambulance reallocation for the reduction of ambulance response times using system status management. *The American Journal of Emergency Medicine*, *33*(2), 159–166. [DOI](https://doi.org/10.1016/j.ajem.2014.10.044)

Li, H., Zhang, J., Zhang, N., & Zhu, B. (2025). Advancing Emergency Care With Digital Twins. *JMIR Aging*, *8*, e71777. [DOI](https://doi.org/10.2196/71777)

Liu, K., Li, X., Zou, C. C., Huang, H., & Fu, Y. (2020). Ambulance Dispatch via Deep Reinforcement Learning. *Proceedings of the 28th International Conference on Advances in Geographic Information Systems*, 123–126. [DOI](https://doi.org/10.1145/3397536.3422204)

Matteson, D. S., McLean, M. W., Woodard, D. B., & Henderson, S. G. (2011). Forecasting emergency medical service call arrival rates. *The Annals of Applied Statistics, 5*(2B), 1379–1406. [DOI](https://doi.org/10.1214/10-AOAS442).

Monks, T., Currie, C. S. M., Onggo, B. S., Robinson, S., Kunc, M., & Taylor, S. J. E. (2019). Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines. *Journal of Simulation, 13*(1), 55–67. [DOI](https://doi.org/10.1080/17477778.2018.1442155).

Monks, T., Harper, A., Allen, M., Collins, L., & Mayne, A. (2023). Forecasting the daily demand for emergency medical ambulances in England and Wales: A benchmark model and external validation. *BMC Medical Informatics and Decision Making, 23*, 117. [DOI](https://doi.org/10.1186/s12911-023-02218-z).

Neira-Rodado, D., Paz-Roa, J. C., Escobar, J. W., & Ortiz-Barrios, M. Á. (2025). A novel machine learning approach for spatiotemporal prediction of EMS events: A case study from Barranquilla, Colombia. *Heliyon*, *11*(2), e41904. [DOI](https://doi.org/10.1016/j.heliyon.2025.e41904)

Ong, M. E. H., Chiam, T. F., Ng, F. S. P., Sultana, P., Lim, S. H., Leong, B. S., Ong, V. Y. K., Ching Tan, E. C., Tham, L. P., Yap, S., Anantharaman, V., & on behalf of the Cardiac Arrest Resuscitation Epidemiology (CARE) Study Group. (2010). Reducing Ambulance Response Times Using Geospatial–Time Analysis of Ambulance Deployment. *Academic Emergency Medicine*, *17*(9), 951–957. [DOI](https://doi.org/10.1111/j.1553-2712.2010.00860.x)

Penfield, R. D., & Giacobbi, P. R., Jr. (2004). Applying a score confidence interval to Aiken's item content-relevance index. *Measurement in Physical Education and Exercise Science, 8*(4), 213–225. [DOI](https://doi.org/10.1207/s15327841mpee0804_3).

Penverne, Y., Martinez, C., Cellier, N., Pehlivan, C., Jenvrin, J., Savary, D., Debierre, V., Deciron, F., Bichri, A., Lebastard, Q., Montassier, E., Leclere, B., & Fontanili, F. (2024). A simulation based digital twin approach to assessing the organization of response to emergency calls. *Npj Digital Medicine*, *7*(1), 385. [DOI](https://doi.org/10.1038/s41746-024-01392-2)

Petri, I., Rezgui, Y., Ghoroghi, A., & Alzahrani, A. (2023). Digital twins for performance management in the built environment. *Journal of Industrial Information Integration*, *33*, 100445. [DOI](https://doi.org/10.1016/j.jii.2023.100445)

Roy, S., Hunter, M., Saroj, A., & Guin, A. (2024). Development of Emergency Vehicle Preemption Strategies on Smart Corridors in a Digital Twin Environment. *Proceedings of the 17th ACM SIGSPATIAL International Workshop on Computational Transportation Science GenAI and Smart Mobility Session*, 12–21. [DOI](https://doi.org/10.1145/3681772.3698213)

Sargent, R. G. (2013). Verification and validation of simulation models. *Journal of Simulation, 7*(1), 12–24. [DOI](https://doi.org/10.1057/jos.2012.20).

Seong, K., Jiao, J., Lewis, R. H., Farahi, A., Navrátil, P., Casebeer, N., Davis, B., Jones, J., & Niyogi, D. (2025). Towards a digital twin for smart resilient cities: Real-time fire and smoke tracking and prediction platform for community awareness (FireCom). *Computational Urban Science*, *5*(1), 49. [DOI](https://doi.org/10.1007/s43762-025-00212-x)

Shahidian, N., Abreu, P., Santos, D., & Barbosa-Povoa, A. (2025). Short-term forecasting of emergency medical services demand exploring machine learning. *Computers & Industrial Engineering*, *200*, 110765. [DOI](https://doi.org/10.1016/j.cie.2024.110765)

Soltani, A., Ullah, S., Hedayatibaei, F., & Muller, A. (2026). Disparities and determinants of EMS response times: A mixed-methods systematic review and LDA-based thematic analysis. *International Journal of Emergency Services*, *15*(2), 233–269. [DOI](https://doi.org/10.1108/IJES-01-2025-0002)

Verma, S., Wilson, F., Wang, H., Smith, L., & Tak, H. J. (2023). Impact of Community Socioeconomic Characteristics on Emergency Medical Service Delays in Responding to Fatal Vehicle Crashes. *AJPM Focus*, *2*(4), 100129. [DOI](https://doi.org/10.1016/j.focus.2023.100129)

Wolf, K., Dawson, R. J., Mills, J. P., Blythe, P., & Morley, J. (2022). Towards a digital twin for supporting multi-agency incident management in a smart city. *Scientific Reports*, *12*(1), 16221. [DOI](https://doi.org/10.1038/s41598-022-20178-8)

Zia, Q., Wang, C., Zhu, S., & Li, Y. (2026). Priority based inter-twin communication in vehicular digital twin networks. *International Journal of Parallel, Emergent and Distributed Systems*, *41*(1), 18–33. [DOI](https://doi.org/10.1080/17445760.2024.2398082)
