# 🎨 GUÍA DE INTEGRACIÓN FRONTEND - Audio en Opciones Múltiples

## 📋 Resumen

Este documento proporciona una guía completa para integrar los nuevos endpoints de audio para opciones múltiples en el frontend de la aplicación.

---

## 🎯 Objetivos de Integración

1. Permitir que usuarios carguen audio para preguntas de opciones
2. Permitir que usuarios carguen audio para respuestas de opciones
3. Permitir que usuarios eliminen audios existentes
4. Proporcionar feedback visual (loading, success, error)
5. Mantener consistencia con la UI existente

---

## 🔗 Endpoints Disponibles

```typescript
// Upload Audio - Pregunta
POST /characters/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/question/audio/

// Upload Audio - Respuesta
POST /characters/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/answer/audio/

// Delete Audio - Pregunta
DELETE /characters/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/question/audio/

// Delete Audio - Respuesta
DELETE /characters/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/answer/audio/
```

---

## 📦 Servicio de API Frontend

### Crear `src/services/audioOptionService.ts`

```typescript
import { API_BASE_URL } from '@/config/api';
import axios, { AxiosInstance } from 'axios';

interface AudioUploadResponse {
  message: string;
  audio_url: string;
  database_url: string;
  urls_match: boolean;
  updated_at: string;
  metadata: {
    size: number;
    format: string;
  };
}

class AudioOptionService {
  private api: AxiosInstance;

  constructor(token: string) {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  /**
   * Sube audio para la pregunta de una opción
   */
  async uploadQuestionAudio(
    characterId: string,
    stateId: string,
    interactionIndex: number,
    optionIndex: number,
    audioFile: File
  ): Promise<AudioUploadResponse> {
    const formData = new FormData();
    formData.append('audio', audioFile);

    const response = await this.api.post<AudioUploadResponse>(
      `/characters/${characterId}/state/${stateId}/interaction/${interactionIndex}/option/${optionIndex}/question/audio/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Sube audio para la respuesta de una opción
   */
  async uploadAnswerAudio(
    characterId: string,
    stateId: string,
    interactionIndex: number,
    optionIndex: number,
    audioFile: File
  ): Promise<AudioUploadResponse> {
    const formData = new FormData();
    formData.append('audio', audioFile);

    const response = await this.api.post<AudioUploadResponse>(
      `/characters/${characterId}/state/${stateId}/interaction/${interactionIndex}/option/${optionIndex}/answer/audio/`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }

  /**
   * Elimina el audio de la pregunta de una opción
   */
  async deleteQuestionAudio(
    characterId: string,
    stateId: string,
    interactionIndex: number,
    optionIndex: number
  ): Promise<void> {
    await this.api.delete(
      `/characters/${characterId}/state/${stateId}/interaction/${interactionIndex}/option/${optionIndex}/question/audio/`
    );
  }

  /**
   * Elimina el audio de la respuesta de una opción
   */
  async deleteAnswerAudio(
    characterId: string,
    stateId: string,
    interactionIndex: number,
    optionIndex: number
  ): Promise<void> {
    await this.api.delete(
      `/characters/${characterId}/state/${stateId}/interaction/${interactionIndex}/option/${optionIndex}/answer/audio/`
    );
  }
}

export default AudioOptionService;
```

---

## 🎛️ Componente de Upload de Audio

### Crear `src/components/AudioUploadButton.tsx`

```typescript
import React, { useState, useRef } from 'react';
import { Button, Tooltip, message, Spin } from 'antd';
import { AudioOutlined, DeleteOutlined } from '@ant-design/icons';
import AudioOptionService from '@/services/audioOptionService';

interface AudioUploadButtonProps {
  characterId: string;
  stateId: string;
  interactionIndex: number;
  optionIndex: number;
  type: 'question' | 'answer';
  hasAudio: boolean;
  audioUrl?: string;
  onUploadSuccess: (audioUrl: string) => void;
  onDeleteSuccess: () => void;
}

const AudioUploadButton: React.FC<AudioUploadButtonProps> = ({
  characterId,
  stateId,
  interactionIndex,
  optionIndex,
  type,
  hasAudio,
  audioUrl,
  onUploadSuccess,
  onDeleteSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const token = localStorage.getItem('token');
  const audioService = new AudioOptionService(token || '');

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validaciones
    const allowedFormats = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'];
    if (!allowedFormats.includes(file.type)) {
      message.error('Formato de audio no válido. Use MP3, WAV, OGG o M4A');
      return;
    }

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      message.error('El archivo es demasiado grande. Máximo 10MB');
      return;
    }

    setLoading(true);
    try {
      let response;
      if (type === 'question') {
        response = await audioService.uploadQuestionAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex,
          file
        );
      } else {
        response = await audioService.uploadAnswerAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex,
          file
        );
      }

      message.success(`Audio de ${type === 'question' ? 'pregunta' : 'respuesta'} cargado exitosamente`);
      onUploadSuccess(response.audio_url);
    } catch (error) {
      message.error(`Error al cargar el audio: ${error.message}`);
      console.error('Error uploading audio:', error);
    } finally {
      setLoading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async () => {
    if (!hasAudio) return;

    setLoading(true);
    try {
      if (type === 'question') {
        await audioService.deleteQuestionAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex
        );
      } else {
        await audioService.deleteAnswerAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex
        );
      }

      message.success(`Audio de ${type === 'question' ? 'pregunta' : 'respuesta'} eliminado`);
      onDeleteSuccess();
    } catch (error) {
      message.error(`Error al eliminar el audio: ${error.message}`);
      console.error('Error deleting audio:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Spin spinning={loading}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={loading}
        />

        <Tooltip title={hasAudio ? 'Reemplazar audio' : 'Subir audio'}>
          <Button
            icon={<AudioOutlined />}
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
            type={hasAudio ? 'primary' : 'default'}
          >
            {hasAudio ? '🎵 Audio' : 'Subir Audio'}
          </Button>
        </Tooltip>

        {hasAudio && (
          <>
            <Tooltip title="Escuchar audio">
              <Button
                icon={<AudioOutlined />}
                onClick={() => {
                  if (audioUrl) {
                    const audio = new Audio(audioUrl);
                    audio.play();
                  }
                }}
                disabled={loading}
              />
            </Tooltip>

            <Tooltip title="Eliminar audio">
              <Button
                icon={<DeleteOutlined />}
                onClick={handleDelete}
                disabled={loading}
                danger
              />
            </Tooltip>
          </>
        )}
      </div>
    </Spin>
  );
};

export default AudioUploadButton;
```

---

## 🎨 Integración en Componente de Opciones

### Actualizar `src/components/OptionEditor.tsx`

```typescript
import React, { useState } from 'react';
import { Card, Row, Col, Input, Button } from 'antd';
import AudioUploadButton from '@/components/AudioUploadButton';

interface OptionEditorProps {
  characterId: string;
  stateId: string;
  interactionIndex: number;
  optionIndex: number;
  option: {
    id: string;
    prompt_user_option: {
      dialog: string;
      audio?: string;
      audio_mp3?: string;
    };
    prompt_user_answer: {
      dialog: string;
      audio?: string;
      audio_mp3?: string;
    };
    prompt_user_guideline: string;
  };
  onUpdate: (field: string, value: string) => void;
  onRefresh: () => void;
}

const OptionEditor: React.FC<OptionEditorProps> = ({
  characterId,
  stateId,
  interactionIndex,
  optionIndex,
  option,
  onUpdate,
  onRefresh,
}) => {
  const [expandedAnswer, setExpandedAnswer] = useState(false);

  const hasQuestionAudio = !!option.prompt_user_option?.audio;
  const hasAnswerAudio = !!option.prompt_user_answer?.audio;

  return (
    <Card
      title={`Opción ${optionIndex + 1}`}
      style={{ marginBottom: '16px' }}
    >
      {/* PREGUNTA */}
      <div style={{ marginBottom: '24px' }}>
        <h4>📝 Pregunta</h4>
        <Row gutter={16}>
          <Col span={16}>
            <Input.TextArea
              value={option.prompt_user_option?.dialog}
              onChange={(e) => onUpdate('question_dialog', e.target.value)}
              placeholder="Texto de la pregunta..."
              rows={3}
            />
          </Col>
          <Col span={8}>
            <AudioUploadButton
              characterId={characterId}
              stateId={stateId}
              interactionIndex={interactionIndex}
              optionIndex={optionIndex}
              type="question"
              hasAudio={hasQuestionAudio}
              audioUrl={option.prompt_user_option?.audio}
              onUploadSuccess={() => onRefresh()}
              onDeleteSuccess={() => onRefresh()}
            />
          </Col>
        </Row>
      </div>

      {/* RESPUESTA */}
      <div style={{ marginBottom: '24px' }}>
        <Button
          onClick={() => setExpandedAnswer(!expandedAnswer)}
          style={{ marginBottom: '12px' }}
        >
          {expandedAnswer ? '▼' : '▶'} Respuesta
        </Button>

        {expandedAnswer && (
          <>
            <Row gutter={16}>
              <Col span={16}>
                <Input.TextArea
                  value={option.prompt_user_answer?.dialog}
                  onChange={(e) => onUpdate('answer_dialog', e.target.value)}
                  placeholder="Texto de la respuesta..."
                  rows={3}
                />
              </Col>
              <Col span={8}>
                <AudioUploadButton
                  characterId={characterId}
                  stateId={stateId}
                  interactionIndex={interactionIndex}
                  optionIndex={optionIndex}
                  type="answer"
                  hasAudio={hasAnswerAudio}
                  audioUrl={option.prompt_user_answer?.audio}
                  onUploadSuccess={() => onRefresh()}
                  onDeleteSuccess={() => onRefresh()}
                />
              </Col>
            </Row>
          </>
        )}
      </div>

      {/* GUÍA */}
      <div>
        <h4>📋 Guía (para la IA)</h4>
        <Input.TextArea
          value={option.prompt_user_guideline}
          onChange={(e) => onUpdate('guideline', e.target.value)}
          placeholder="Instrucciones de cómo debe responder la IA..."
          rows={2}
        />
      </div>
    </Card>
  );
};

export default OptionEditor;
```

---

## 🔄 Manejadores de Estado (React Hooks)

### Crear `src/hooks/useOptionAudio.ts`

```typescript
import { useState, useCallback } from 'react';
import AudioOptionService from '@/services/audioOptionService';

interface UseOptionAudioProps {
  characterId: string;
  stateId: string;
  interactionIndex: number;
  optionIndex: number;
  token: string;
}

export const useOptionAudio = ({
  characterId,
  stateId,
  interactionIndex,
  optionIndex,
  token,
}: UseOptionAudioProps) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const audioService = new AudioOptionService(token);

  const uploadQuestionAudio = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const response = await audioService.uploadQuestionAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex,
          file
        );
        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Error uploading audio';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [characterId, stateId, interactionIndex, optionIndex]
  );

  const uploadAnswerAudio = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const response = await audioService.uploadAnswerAudio(
          characterId,
          stateId,
          interactionIndex,
          optionIndex,
          file
        );
        return response;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Error uploading audio';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [characterId, stateId, interactionIndex, optionIndex]
  );

  const deleteQuestionAudio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await audioService.deleteQuestionAudio(
        characterId,
        stateId,
        interactionIndex,
        optionIndex
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error deleting audio';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [characterId, stateId, interactionIndex, optionIndex]);

  const deleteAnswerAudio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await audioService.deleteAnswerAudio(
        characterId,
        stateId,
        interactionIndex,
        optionIndex
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Error deleting audio';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [characterId, stateId, interactionIndex, optionIndex]);

  return {
    loading,
    error,
    uploadQuestionAudio,
    uploadAnswerAudio,
    deleteQuestionAudio,
    deleteAnswerAudio,
  };
};
```

---

## 📝 Validaciones Frontend

### Crear `src/utils/audioValidation.ts`

```typescript
export const AUDIO_FORMATS = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a'];
export const MAX_AUDIO_SIZE = 10 * 1024 * 1024; // 10MB
export const MAX_AUDIO_DURATION = 5 * 60; // 5 minutos

export interface AudioValidationError {
  type: 'format' | 'size' | 'duration';
  message: string;
}

export async function validateAudioFile(file: File): Promise<AudioValidationError | null> {
  // Validar formato
  if (!AUDIO_FORMATS.includes(file.type)) {
    return {
      type: 'format',
      message: 'Formato de audio no válido. Use MP3, WAV, OGG o M4A',
    };
  }

  // Validar tamaño
  if (file.size > MAX_AUDIO_SIZE) {
    return {
      type: 'size',
      message: `El archivo es demasiado grande. Máximo 10MB (${(file.size / 1024 / 1024).toFixed(2)}MB)`,
    };
  }

  // Validar duración
  try {
    const duration = await getAudioDuration(file);
    if (duration > MAX_AUDIO_DURATION) {
      return {
        type: 'duration',
        message: `El audio es demasiado largo. Máximo 5 minutos (${(duration / 60).toFixed(2)}m)`,
      };
    }
  } catch (error) {
    console.warn('Could not validate audio duration:', error);
  }

  return null;
}

export function getAudioDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContext.decodeAudioData(
        reader.result as ArrayBuffer,
        (buffer) => {
          resolve(buffer.duration);
        },
        (error) => {
          reject(error);
        }
      );
    };
    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };
    reader.readAsArrayBuffer(file);
  });
}
```

---

## 🎯 Ejemplo de Uso Completo

```typescript
// En el componente principal
import React, { useState } from 'react';
import OptionEditor from '@/components/OptionEditor';

const OptionsPage: React.FC = () => {
  const [options, setOptions] = useState(/* datos de opciones */);
  const characterId = 'char_123';
  const stateId = 'state_456';
  const interactionIndex = 0;

  const handleOptionUpdate = (optionIndex: number, field: string, value: string) => {
    // Actualizar estado local
    const newOptions = [...options];
    // ...update logic...
    setOptions(newOptions);
  };

  const handleRefresh = async () => {
    // Recargar datos del servidor
    // ...fetch logic...
  };

  return (
    <div>
      {options.map((option, index) => (
        <OptionEditor
          key={option.id}
          characterId={characterId}
          stateId={stateId}
          interactionIndex={interactionIndex}
          optionIndex={index}
          option={option}
          onUpdate={(field, value) => handleOptionUpdate(index, field, value)}
          onRefresh={handleRefresh}
        />
      ))}
    </div>
  );
};

export default OptionsPage;
```

---

## 🧪 Testing

### Tests unitarios para `audioOptionService.ts`

```typescript
import AudioOptionService from '@/services/audioOptionService';

describe('AudioOptionService', () => {
  let service: AudioOptionService;
  const token = 'test-token';

  beforeEach(() => {
    service = new AudioOptionService(token);
  });

  test('should upload question audio successfully', async () => {
    const file = new File(['audio data'], 'test.mp3', { type: 'audio/mpeg' });
    
    const result = await service.uploadQuestionAudio(
      'char_123',
      'state_456',
      0,
      0,
      file
    );

    expect(result.audio_url).toBeDefined();
    expect(result.message).toBe('Audio updated successfully');
  });

  test('should delete question audio successfully', async () => {
    await expect(
      service.deleteQuestionAudio('char_123', 'state_456', 0, 0)
    ).resolves.not.toThrow();
  });
});
```

---

## 📊 Flujo de Datos

```
Usuario selecciona archivo
    ↓
Frontend valida archivo
    ↓
Frontend muestra loading
    ↓
Frontend llama AudioUploadButton
    ↓
AudioOptionService.uploadQuestionAudio()
    ↓
POST /characters/{id}/state/{state}/interaction/0/option/0/question/audio/
    ↓
Backend procesa archivo
    ↓
Backend sube a Google Cloud Storage
    ↓
Backend actualiza MongoDB
    ↓
Backend retorna URL
    ↓
Frontend recibe respuesta
    ↓
Frontend muestra success toast
    ↓
Frontend recarga datos
    ↓
UI actualiza con nuevo audio
```

---

## 🚀 Checklist de Integración

- [ ] Crear `AudioOptionService`
- [ ] Crear `AudioUploadButton` component
- [ ] Crear `useOptionAudio` hook
- [ ] Crear `audioValidation` utilities
- [ ] Integrar en `OptionEditor`
- [ ] Agregar tests unitarios
- [ ] Agregar tests de integración
- [ ] Validar en desarrollo
- [ ] Validar en staging
- [ ] Deploy a producción

---

## 📞 Soporte

Para dudas sobre integración:

1. **Backend funcionando**: `http://localhost:8000/docs`
2. **Ejemplos de respuesta**: Ver `IMPLEMENTACION_AUDIO_OPCIONES.md`
3. **Tests**: Ver `test_option_audio_endpoints.http`

---

**Guía de Integración Completa** ✅
