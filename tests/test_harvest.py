"""Regressões que protegem evidência e identidade em uma segunda colheita."""

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import audit_10_harvest as harvest
import audit_13_resolve_scholar as resolver


class AtualizacaoTest(unittest.TestCase):
    def setUp(self):
        self.antigo = {
            "id": "airline_s007",
            "doi": "10.1000/antigo",
            "title": "Um título suficientemente longo para identificação exata",
            "status": "aresta_falsa",
            "text_path": "text/evidencia.txt",
            "source_id": "periodico-verificado",
            "src": ["scholar"],
        }

    def test_recoleta_preserva_evidencia_ids_e_veredito(self):
        novo = {
            "doi": self.antigo["doi"],
            "title": "Título externo diferente",
            "status": "oa_baixavel",
            "src": ["openalex"],
        }
        baseline = copy.deepcopy(self.antigo)
        result = harvest.atualizar_registros("airline", [self.antigo], [novo])[0]
        for key in ("id", "title", "status", "text_path", "source_id"):
            self.assertEqual(result[key], self.antigo[key])
        self.assertEqual(result["src"], ["openalex", "scholar"])
        self.assertEqual(self.antigo, baseline)

    def test_fonte_vazia_nao_apaga_inventario(self):
        self.assertEqual(
            harvest.atualizar_registros("airline", [self.antigo], []), [self.antigo]
        )

    def test_versoes_preexistentes_nao_sao_rededuplicadas(self):
        outro = {**self.antigo, "id": "airline_011", "doi": "10.1000/versao"}
        result = harvest.atualizar_registros("airline", [self.antigo, outro], [])
        self.assertEqual([r["id"] for r in result], ["airline_s007", "airline_011"])

    def test_candidato_sem_titulo_casa_apos_uniao_das_fontes(self):
        novos = [
            {"doi": "10.1000/preprint", "src": ["opencitations"]},
            {"doi": "10.1000/preprint", "title": self.antigo["title"], "src": ["s2"]},
        ]
        result = harvest.atualizar_registros("airline", [self.antigo], novos)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["doi"], self.antigo["doi"])
        self.assertIn("10.1000/preprint", result[0]["alternate_dois"])

    def test_orfa_deliberada_nao_ressuscita(self):
        novo = {"doi": "10.1000/arquivado", "title": "Outra obra"}
        result = harvest.atualizar_registros(
            "airline", [self.antigo], [novo], {"10.1000/arquivado"}
        )
        self.assertEqual(result, [self.antigo])

    def test_ids_novos_sao_estaveis_e_sem_colisao(self):
        antigo = {**self.antigo, "id": "airline_011"}
        novos = [
            {"doi": "10.1000/z", "title": "Outra obra Z"},
            {"doi": "10.1000/a", "title": "Outra obra A"},
        ]
        a = harvest.atualizar_registros("airline", [antigo], novos)
        b = harvest.atualizar_registros("airline", a, list(reversed(novos)))
        self.assertEqual(a, b)
        self.assertEqual(
            [r["id"] for r in a], ["airline_011", "airline_012", "airline_013"]
        )

    def test_indisponibilidade_nao_parece_zero_citacoes(self):
        with (
            patch.object(harvest.auditlib, "jget", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            harvest.json_da_fonte("https://example.test/api")
        with patch.object(harvest.auditlib, "jget", return_value=[]):
            self.assertEqual(harvest.json_da_fonte("https://example.test/api"), [])


class ResolucaoTest(unittest.TestCase):
    def test_titulo_vazio_nao_casa_e_nao_apaga_titulo_original(self):
        rec = {
            "title": "Provlepsi kathysterisis ptiseon me technikes michanikis mathisis",
            "doi": None,
        }
        responses = [
            {
                "message": {
                    "items": [{"DOI": "10.3030/687772", "title": [], "type": "grant"}]
                }
            },
            {"results": []},
        ]
        with patch.object(resolver.auditlib, "jget", side_effect=responses):
            got = resolver.resolve(rec.copy())
        self.assertIsNone(got["doi"])
        self.assertEqual(got["title"], rec["title"])

    def test_titulo_completo_valido_casa_com_scholar_truncado(self):
        full = "An empirical investigation of airline delay determinants and airport congestion"
        self.assertTrue(resolver.titulo_compativel(full[:55].lower(), full.lower()))
        self.assertFalse(resolver.titulo_compativel(full[:55].lower(), ""))
        self.assertFalse(resolver.titulo_compativel(full[:55].lower(), "an"))


if __name__ == "__main__":
    unittest.main()
