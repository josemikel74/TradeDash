class AgentPlaceholder:
    """Clase base temporal para los agentes de la Fase 2."""
    def __init__(self, name):
        self.name = name

    def status(self):
        return f"✅ El agente '{self.name}' se encuentra inicializado y a la espera de instrucciones."

class RiskManager(AgentPlaceholder):
    def __init__(self):
        super().__init__("Gestor de Riesgo y Capital")

class Analyst(AgentPlaceholder):
    def __init__(self):
        super().__init__("Analista Cuantitativo de Mercado")

class Executor(AgentPlaceholder):
    def __init__(self):
        super().__init__("Ejecutor de Órdenes")
