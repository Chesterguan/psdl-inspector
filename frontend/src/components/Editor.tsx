'use client';

import { useEffect, useRef, useCallback } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState } from '@codemirror/state';
import { yaml } from '@codemirror/lang-yaml';
import { oneDark } from '@codemirror/theme-one-dark';

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export default function Editor({ value, onChange, className = '' }: EditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  // Handle external value changes
  const updateListener = useCallback(
    (update: { docChanged: boolean; state: EditorState }) => {
      if (update.docChanged) {
        onChange(update.state.doc.toString());
      }
    },
    [onChange]
  );

  useEffect(() => {
    if (!editorRef.current) return;

    const state = EditorState.create({
      doc: value,
      extensions: [
        basicSetup,
        yaml(),
        oneDark,
        EditorView.updateListener.of(updateListener),
        EditorView.theme({
          '&': {
            height: '100%',
            fontSize: '14px',
          },
          '.cm-scroller': {
            overflow: 'auto',
            fontFamily: 'ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, Liberation Mono, monospace',
          },
          '.cm-content': {
            padding: '8px 0',
          },
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: editorRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount - intentionally excluding deps

  // Update editor content when value prop changes externally
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentContent = view.state.doc.toString();
    if (currentContent !== value) {
      view.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: value,
        },
      });
    }
  }, [value]);

  return (
    <div
      ref={editorRef}
      className={`border border-gray-700 rounded-lg overflow-hidden bg-[#282c34] ${className}`}
    />
  );
}
