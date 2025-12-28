class ClusterCalculator:
    def __init__(self):
        # Definido como 5 para respeitar o limite de realocação do servidor por conta/dia
        self.SUBORDINATES_PER_GENERAL = 5 

    def calculate(self, total_accounts, master_name, pool_accounts):
        """
        Calcula a estrutura piramidal baseada no limite de 5 subordinados.
        
        Args:
            total_accounts: Número total de contas (incluindo o Master)
            master_name: Nome de usuário da conta Master
            pool_accounts: Lista com os nomes das contas disponíveis no pool
        """
        
        # O Master precisa de pelo menos 5 generais para iniciar a estrutura base 5
        if total_accounts < 6: 
            return {
                "is_valid": False,
                "message": f"Precisa de no mínimo 6 contas (1 Master + 5 Generais). Você tem {total_accounts}."
            }
        
        structure = self._build_pyramid(total_accounts, master_name, pool_accounts)
        
        return {
            "is_valid": True,
            "structure": structure,
            "accounts_used": structure["total_used"],
            "accounts_unused": len(pool_accounts) + 1 - structure["total_used"],
            "message": f"Estrutura base 5 calculada: {structure['total_used']} contas serão utilizadas."
        }

    def _build_pyramid(self, total, master, pool):
        """
        Constrói a árvore lógica garantindo no máximo 5 filhos por nó pai.
        Retorna um dicionário estruturado e uma lista de relações direta.
        """
        
        structure = {
            "master": master,
            "generals": [],      # Generais diretos do Master (Nível 1)
            "total_used": 1,     # Inicia contagem pelo Master
            "levels": [],        # Níveis subsequentes (Nível 2+)
            "relations": {}      # Mapeamento Direto { 'Filho': 'Pai' }
        }
        
        used = 1
        # Filtra o pool para garantir que o Master não esteja nele
        available_pool = [a for a in pool if a != master]
        pool_idx = 0
        
        # --- NÍVEL 1: Os 5 Generais diretos do Master ---
        generals_l1 = []
        for i in range(self.SUBORDINATES_PER_GENERAL):
            if pool_idx >= len(available_pool):
                break
            
            gen_name = available_pool[pool_idx]
            generals_l1.append({
                "name": gen_name,
                "parent": master,
                "subordinates": [] 
            })
            structure["relations"][gen_name] = master # Define relação de convite
            used += 1
            pool_idx += 1
        
        structure["generals"] = generals_l1
        
        # --- NÍVEL 2 EM DIANTE: Subordinados em cascata ---
        # Fila de pais que podem receber subordinados
        parents_queue = list(generals_l1)
        level_num = 2
        
        while parents_queue and pool_idx < len(available_pool):
            next_level_parents = []
            
            for parent_obj in parents_queue:
                # Cada pai recebe no máximo 5 subordinados
                for j in range(self.SUBORDINATES_PER_GENERAL):
                    if pool_idx >= len(available_pool):
                        break
                    
                    sub_name = available_pool[pool_idx]
                    parent_obj["subordinates"].append(sub_name)
                    structure["relations"][sub_name] = parent_obj["name"] # Define quem convida quem
                    used += 1
                    pool_idx += 1
                    
                    # O primeiro subordinado (j=0) torna-se o General do próximo nível
                    if j == 0:
                        new_gen_obj = {
                            "name": sub_name,
                            "parent": parent_obj["name"],
                            "subordinates": []
                        }
                        next_level_parents.append(new_gen_obj)
            
            if next_level_parents:
                structure["levels"].append({
                    "level": level_num,
                    "nodes": next_level_parents,
                    "total_nodes": len(next_level_parents)
                })
            
            parents_queue = next_level_parents
            level_num += 1

        structure["total_used"] = used
        return structure

    def visualize(self, structure):
        """Gera uma representação visual para o log do bot."""
        output = f"\n{'='*60}\n"
        output += f"ESTRUTURA DO CLUSTER (BASE 5)\n"
        output += f"{'='*60}\n"
        output += f"👑 MASTER: {structure['master']}\n"
        
        for i, gen in enumerate(structure['generals'], 1):
            sub_count = len(gen['subordinates'])
            output += f"  ├─ General {i}: {gen['name']} ({sub_count} subordinados)\n"
            for j, sub in enumerate(gen['subordinates']):
                connector = "  │  └─" if j == sub_count - 1 else "  │  ├─"
                is_gen = " [GEN L{}]".format(i+1) if j == 0 else ""
                output += f"{connector} {sub}{is_gen}\n"
        
        output += f"\nTotal de contas na pirâmide: {structure['total_used']}\n"
        output += f"{'='*60}\n"
        return output

# Instância global
cluster_calculator = ClusterCalculator()