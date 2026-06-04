# Alex Voice — Tests del Plan A

## 📋 Cobertura de Tests

| # | Test | Tipo | Automático | Descripción |
|:-:|:-----|:----:|:----------:|:------------|
| 1 | Servidores activos | ✅ | Sí | Verifica que monitor server (3000) y llama-server (8081) respondan |
| 2 | API /api/stats | ✅ | Sí | VRAM, RAM, GPU, CPU, temperatura, tokens/s |
| 3 | API /api/logs | ✅ | Sí | Endpoint de logging para el panel debug |
| 4 | TTS Español | ✅ | Sí | Piper genera WAV con modelo `es_ES-sharvard-medium` |
| 5 | TTS Inglés | ✅ | Sí | Piper genera WAV con modelo `en_US-lessac-medium` |
| 6 | TTS Japonés | ✅ | Sí | Servidor responde (frontend usa Chrome SpeechSynthesis) |
| 7 | Modo Teacher (ES) | ✅ | Sí* | Prompt educativo en español |
| 8 | Modo Teacher (EN) | ✅ | Sí* | Prompt educativo en inglés |
| 9 | Modo Conversación (ES) | ✅ | Sí* | Prompt conversacional en español |
| 10 | Modo Traductor (JA→ES) | ✅ | Sí* | Traducción de japonés a español |
| 11 | Modo Traductor (EN→ES) | ✅ | Sí* | Traducción de inglés a español |
| 12 | Modelos de voz | ✅ | Sí | Verifica archivos .onnx existan |
| 13 | Piper ejecutable | ✅ | Sí | Verifica `bin/piper/piper.exe` exista |
| 14 | Debug Panel | ✅ | Manual | Abrir `http://localhost:3000/debug` |
| 15 | Japonés QA | ✅ | Manual | Verificar caracteres japoneses en UI |

*Tests con LLM se saltan con `--quick`

## 🚀 Cómo Ejecutar

```bash
# 1. Asegúrate de que los servidores estén corriendo
python server.py              # Monitor server (puerto 3000)
# llama-server debe estar corriendo (puerto 8081)

# 2. Ejecuta los tests
cd /c/Users/andyh/Desktop/Soft/Alex_Voice
bash tests/test_plan_a.sh          # Todos los tests (incluye LLM)
bash tests/test_plan_a.sh --quick  # Solo tests rápidos (sin LLM)
bash tests/test_plan_a.sh --verbose  # Output detallado
```

## 🎯 Pruebas Subjetivas (Manuales)

Además de los tests automáticos, verifica manualmente:

### Calidad de Voz
- **Español**: Debe sonar natural, clara, sin errores de pronunciación
- **Inglés**: Debe usar fonética inglesa real, no acento español
- **Japonés**: Chrome SpeechSynthesis — seleccionar voz japonesa

### Modos
1. **🎓 Teacher**: Pide explicaciones complejas → debe ser estructurado y claro
2. **💬 Conversación**: Conversación natural → debe ser fluido y contextual
3. **🌍 Traductor**: "Traduce 'X' al español/japonés/inglés" → debe ser preciso

### Rendimiento
- TTS debe generar en <2 segundos para textos normales
- Tokens/s debe mostrar valores no-cero durante generación
- VRAM debe reflejar el uso real del modelo Qwen

## 📊 Panel de Depuración

Abre `http://localhost:3000/debug` para ver en tiempo real:
- Todos los inputs/outputs del LLM
- Eventos TTS con modelo de voz usado
- Idiomas detectados automáticamente
- Snapshot de hardware en cada petición
- Filtros por tipo, idioma, y modo
