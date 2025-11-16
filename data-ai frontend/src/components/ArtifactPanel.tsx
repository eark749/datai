import { Button } from './ui/button';
import { X, Maximize2, Minimize2, Edit2, Check } from 'lucide-react';
import { Artifact } from './ChatInterface';
import { useState } from 'react';
import { Input } from './ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

interface ArtifactPanelProps {
  artifacts: Artifact[];
  activeArtifactId: string;
  onClose: (artifactId: string) => void;
  onCloseAll: () => void;
  onSwitchArtifact: (artifactId: string) => void;
  onRenameArtifact: (artifactId: string, newName: string) => void;
}

export function ArtifactPanel({ 
  artifacts, 
  activeArtifactId,
  onClose, 
  onCloseAll,
  onSwitchArtifact,
  onRenameArtifact 
}: ArtifactPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');

  const activeArtifact = artifacts.find(a => a.id === activeArtifactId) || artifacts[0];

  const handleStartEdit = (artifact: Artifact) => {
    setEditingId(artifact.id);
    setEditingName(artifact.name);
  };

  const handleSaveEdit = (artifactId: string) => {
    if (editingName.trim()) {
      onRenameArtifact(artifactId, editingName.trim());
    }
    setEditingId(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent, artifactId: string) => {
    if (e.key === 'Enter') {
      handleSaveEdit(artifactId);
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  if (!activeArtifact) return null;

  return (
    <div
      className={`bg-white border-l border-slate-200 flex flex-col shadow-2xl transition-all duration-300 ${
        isExpanded ? 'w-full' : 'w-[700px]'
      }`}
      role="complementary"
      aria-label="Artifact viewer panel"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-4 shadow-lg">
        <div className="flex items-center justify-between mb-2">
          <div className="flex-1 min-w-0">
            <h2 className="text-white text-lg">Artifact Dashboard</h2>
            <p className="text-purple-100 text-sm">
              {artifacts.length} {artifacts.length === 1 ? 'artifact' : 'artifacts'} open
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setIsExpanded(!isExpanded)}
              variant="ghost"
              size="sm"
              className="h-9 w-9 p-0 text-white hover:bg-white/20"
              aria-label={isExpanded ? 'Minimize panel' : 'Maximize panel'}
            >
              {isExpanded ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
            <Button
              onClick={onCloseAll}
              variant="ghost"
              size="sm"
              className="h-9 w-9 p-0 text-white hover:bg-white/20"
              aria-label="Close all artifacts"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs for multiple artifacts */}
      {artifacts.length > 1 ? (
        <Tabs 
          value={activeArtifactId} 
          onValueChange={onSwitchArtifact}
          className="flex-1 flex flex-col overflow-hidden"
        >
          <TabsList className="w-full justify-start rounded-none border-b bg-slate-50 p-0 h-auto overflow-x-auto">
            {artifacts.map(artifact => (
              <TabsTrigger
                key={artifact.id}
                value={artifact.id}
                className="group relative rounded-none border-b-2 border-transparent data-[state=active]:border-purple-600 data-[state=active]:bg-white px-4 py-3 gap-2 flex items-center"
              >
                {editingId === artifact.id ? (
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <Input
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, artifact.id)}
                      className="h-6 text-sm w-32"
                      autoFocus
                      onBlur={() => handleSaveEdit(artifact.id)}
                    />
                    <Button
                      onClick={() => handleSaveEdit(artifact.id)}
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0"
                    >
                      <Check className="h-3 w-3" />
                    </Button>
                  </div>
                ) : (
                  <>
                    <span className="truncate max-w-[120px]">{artifact.name}</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartEdit(artifact);
                        }}
                        size="sm"
                        variant="ghost"
                        className="h-5 w-5 p-0 hover:bg-slate-200"
                        aria-label={`Rename ${artifact.name}`}
                      >
                        <Edit2 className="h-3 w-3" />
                      </Button>
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          onClose(artifact.id);
                        }}
                        size="sm"
                        variant="ghost"
                        className="h-5 w-5 p-0 hover:bg-red-100 hover:text-red-600"
                        aria-label={`Close ${artifact.name}`}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </>
                )}
              </TabsTrigger>
            ))}
          </TabsList>

          {artifacts.map(artifact => (
            <TabsContent 
              key={artifact.id} 
              value={artifact.id}
              className="flex-1 m-0 overflow-auto bg-slate-50"
            >
              <iframe
                srcDoc={artifact.htmlContent}
                className="w-full h-full border-0"
                title={artifact.name}
                sandbox="allow-scripts allow-same-origin"
              />
            </TabsContent>
          ))}
        </Tabs>
      ) : (
        // Single artifact view
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="bg-slate-50 border-b px-4 py-3 flex items-center justify-between">
            {editingId === activeArtifact.id ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editingName}
                  onChange={(e) => setEditingName(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, activeArtifact.id)}
                  className="h-7 text-sm"
                  autoFocus
                  onBlur={() => handleSaveEdit(activeArtifact.id)}
                />
                <Button
                  onClick={() => handleSaveEdit(activeArtifact.id)}
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                >
                  <Check className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <>
                <h3 className="text-black">{activeArtifact.name}</h3>
                <Button
                  onClick={() => handleStartEdit(activeArtifact)}
                  size="sm"
                  variant="ghost"
                  className="h-7 px-2"
                  aria-label={`Rename ${activeArtifact.name}`}
                >
                  <Edit2 className="h-3 w-3 mr-1" />
                  Rename
                </Button>
              </>
            )}
          </div>
          <div className="flex-1 overflow-auto bg-slate-50">
            <iframe
              srcDoc={activeArtifact.htmlContent}
              className="w-full h-full border-0"
              title={activeArtifact.name}
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
        </div>
      )}
    </div>
  );
}
