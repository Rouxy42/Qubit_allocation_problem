# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 10:16:20 2026

@author: Jérôme Rouzé

Ce fichier ne doit pas être modifié 
Toutes modifications pourrait entrainer des bugs
ou des changements indésirables des instances.
    
Il n'est pas nécessaire de comprendre que ce fait ce code.
Il est là uniquement pour charger les instances.   
"""

from qiskit import QuantumCircuit
from qiskit.transpiler import Layout
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

##-------------------------------------------------------
##     Création du backend (machine quantique)
##-------------------------------------------------------
from qiskit.providers import BackendV2
from qiskit.providers.options import Options
from qiskit.providers.exceptions import QiskitError
class CustomBackend(BackendV2):
    def __init__(self, target, coupling):
        super().__init__(name="custom_basis_backend")
        self._target = target
        self._coupling = coupling

    @property
    def target(self):
        return self._target

    @property
    def coupling_map(self):
        return self._coupling

    @classmethod
    def _default_options(cls):
        return Options(shots=1024)
    
    @property
    def max_circuits(self):
        return 1
    
    def run(self, run_input, **options):
        raise QiskitError(
            "This backend is for transpilation only and does not support execution."
        )
                
def backend_selector(num_physical_qubit):
    if num_physical_qubit == 20:
        ### Backend
        from qiskit.providers.fake_provider import Fake20QV1
        from qiskit.providers import BackendV2Converter
        
        backend = Fake20QV1()
        backend = BackendV2Converter(backend)
        
       
    elif num_physical_qubit == 27:
        ### Backend
        from qiskit.providers.fake_provider import Fake27QPulseV1
        from qiskit.providers import BackendV2Converter
        
        backend = Fake27QPulseV1()
        backend = BackendV2Converter(backend)
        
    else:
        from qiskit.transpiler import CouplingMap
        
        coupling = CouplingMap([
            (0,1), (1,2), (2,3), (3,4), (4,5), (5,6), (6,7), (7,8), (8,9), (9,10), (10,11), (11,12), (12,13),
            (13,14), (14,15), (0,15), (1,14), (2,13), (3,12), (4,11), (5,10), (6,9)
        ])
        
        from qiskit.transpiler import Target
        from qiskit.circuit.library import IGate, XGate, CXGate, RZGate, SXGate, Reset
        from qiskit.circuit import Measure
        
        target = Target(num_qubits=16)
        
        # 1-qubit gates
        target.add_instruction(IGate(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(XGate(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(SXGate(),  {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(RZGate(0), {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(Reset(),   {(q,): None for q in range(target.num_qubits)})
        target.add_instruction(Measure(), {(q,): None for q in range(target.num_qubits)})
        
        # 2-qubit gates follow coupling graph
        cx_edges = set(coupling.get_edges())
        cx_edges |= {(b, a) for (a, b) in coupling.get_edges()}
        target.add_instruction(CXGate(), {edge: None for edge in cx_edges})

        backend = CustomBackend(target, coupling)
    return backend


##-------------------------------------------------------
##     Selection de l'instance du probleme
##-------------------------------------------------------
def instance_selector(instance_num):
    if instance_num == 1 or instance_num == 2 or instance_num == 3 or instance_num == 11:
        backend = backend_selector(16)
    elif instance_num == 4 or instance_num == 5 or  instance_num == 6 or instance_num == 12:
        backend = backend_selector(20)
    elif instance_num == 7 or instance_num == 8 or  instance_num == 9 or instance_num == 13:
        backend = backend_selector(27)
    else:
        print("Choix d'une instance inexistance, instance 1 revoyé  par défaut")
        backend = backend_selector(16)
        instance_num = 1
        
    qasmfile = f".\Instances\Instance_{instance_num}.qasm"  ###### Il est possible de cette ligne soit problèmatique.
    circuit = QuantumCircuit().from_qasm_file(qasmfile)
    circuit.remove_final_measurements()
    
    n = circuit.num_qubits
    m = backend.num_qubits
    
    return backend,circuit,n,m

def fitness_inner(mapping,circuit,backend):
    qr=circuit.qregs[0]
    init_mapping = {qr[i]:mapping[i] for i in range(len(mapping))}
    init_mapping = Layout(init_mapping)

    pm = generate_preset_pass_manager(3,backend,initial_layout=init_mapping)
    pm.layout.remove(1)
    pm.layout.remove(1)

    QC=pm.run(circuit)
    return QC.depth()