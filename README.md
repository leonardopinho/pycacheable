# PyCacheable

Decorator de cache para métodos e funções Python com backends em memória e SQLite — serialização automática, hash estável de parâmetros, suporte a instância/estado e arquitetura plugável.

---

## Problema

Em muitos aplicativos Python existem métodos que:

- fazem consultas repetidas ao banco de dados ou a APIs externas;
- recebem os mesmos parâmetros múltiplas vezes;
- repetem trabalho caro de CPU ou I/O;
- ou seja: fazem **o mesmo trabalho mais de uma vez**, desperdiçando tempo e recursos.

Sem um mecanismo de cache, cada chamada resulta em reexecução completa, levando a latências elevadas, carga extra no banco/serviço, e experiência de usuário piorada.

---

## Solução

A biblioteca fornece:

- Um decorator `@cacheable(...)` que envolve funções ou métodos, gera uma **chave estável** a partir dos parâmetros (serialização canônica + sha256);
- Suporte a backends:
  - `InMemoryCache`: cache volátil em memória com LRU + TTL.
  - `SQLiteCache`: cache persistente em disco (SQLite) com TTL, ideal para entre execuções ou processos;
- Logs claros de fluxo: HIT / MISS / EXPIRE — permitindo entender se o cache está funcionando;
- Métodos auxiliares:
  - `.cache_clear()`, `.cache_info()` no wrapper para inspeção/manutenção;

---

## Como usar

```python
from src.pycacheable.backend_sqlite import SQLiteCache
from src.pycacheable.backend_memory import InMemoryCache
from src.pycacheable.cacheable import cacheable

mem = InMemoryCache(max_entries=512)
disk = SQLiteCache(path="./.cache/myapp.sqlite")


class Repo:
    @cacheable(ttl=60, backend=mem)
    def get_user(self, user_id: int) -> dict:
        # consulta cara ao banco
        return {"user_id": user_id, "name": f"user{user_id}"}

    @cacheable(ttl=300, backend=disk)
    def get_orders(self, user_id: int, status: str = "open") -> list:
        return [{"order_id": 101, "user_id": user_id, "status": status}]


repo = Repo()
u1 = repo.get_user(42)  # MISS → executa consulta
u2 = repo.get_user(42)  # HIT → retorna cache, consulta não é executada
```

---

## Benefícios

- Menor latência em chamadas repetidas (hit quase instantâneo).  
- Menor carga no banco/serviço, menos I/O repetido.  
- Persistência local (via SQLite) permite cache entre reinícios/processos.  
- Transparente para o usuário da função — apenas aplicar o decorator.  
- Logs e métricas ajudam a monitorar impacto real.

---

## Quando usar

- Funções/métodos com **resultado determinístico** (mesmos parâmetros → mesmo resultado)  
- Consultas idempotentes e repetidas  
- Cálculos caros de CPU ou I/O  
- Cenários onde latência importa e repetição deve ser evitada

---

## Considerações e limites

- O cache evita reexecuções **somente** se os parâmetros para o método forem os mesmos e serializáveis.  
- Se o método depende de estados mutáveis fora dos parâmetros (ex.: `self.some_state`), você deve usar `include_self=True` ou custom `key_fn`.  
- TTL é usado para expiração — resultados podem ficar “stale” se parâmetros ou contexto mudarem sem mudar a chave.  
- Embora o backend SQLite seja persistente, ele **não substitui** um cache distribuído (ex.: Redis) em cenários multi‑processo/semi‑distribuídos.

---

## Benchmarks

Veja resultados reais que medem MISS vs HIT:

| Backend | MISS (s) | HIT (s) | Speedup | Calls |
|----------|-----------|----------|----------|--------|
| RAW | 0.6827 | — | — | — |
| InMemory | 0.6630 | 0.000113 | ~5 870× | 1 |
| SQLite | 0.7157 | 0.000098 | ~7 300× | 1 |

O cache reduz o tempo de execução de ~0.68 s para ~0.0001 s — um **speedup superior a 5 000×**.

---

## Próximos passos

- Suporte a funções `async def` (decorator awaitable)   
- Backend Redis / LMDB para cenários distribuídos  
- Métricas e integração com Prometheus  

---

## Licença

MIT License — veja o arquivo `LICENSE` para detalhes.