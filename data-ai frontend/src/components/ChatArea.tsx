import { useState, useEffect, useRef } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { Send, Database, FileText, ChevronDown } from 'lucide-react';
import { ChatSession, DatabaseConnection, Artifact } from './ChatInterface';

interface ChatAreaProps {
  currentChat?: ChatSession;
  onSendMessage: (text: string, selectedDbIds?: string[]) => void;
  dbConnections: DatabaseConnection[];
  onArtifactClick: (artifact: Artifact) => void;
}

export function ChatArea({
  currentChat,
  onSendMessage,
  dbConnections,
  onArtifactClick,
}: ChatAreaProps) {
  const [inputValue, setInputValue] = useState('');
  const [selectedDbIds, setSelectedDbIds] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentChat?.messages]);

  // Auto-select default DBs on mount
  useEffect(() => {
    const defaultDbs = dbConnections.filter(db => db.isDefault);
    if (defaultDbs.length > 0 && selectedDbIds.length === 0) {
      setSelectedDbIds(defaultDbs.map(db => db.id));
    }
  }, [dbConnections]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    onSendMessage(inputValue, selectedDbIds.length > 0 ? selectedDbIds : undefined);
    setInputValue('');
  };

  const handleToggleDb = (dbId: string) => {
    setSelectedDbIds(prev =>
      prev.includes(dbId)
        ? prev.filter(id => id !== dbId)
        : [...prev, dbId]
    );
  };

  const handleSelectAll = () => {
    setSelectedDbIds(dbConnections.map(db => db.id));
  };

  const handleDeselectAll = () => {
    setSelectedDbIds([]);
  };

  if (!currentChat) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white">
        <div className="text-center">
          <h2 className="text-black mb-2">No Chat Selected</h2>
          <p className="text-gray-600">Select a chat or create a new one to get started</p>
        </div>
      </div>
    );
  }

  const selectedDbs = dbConnections.filter(db => selectedDbIds.includes(db.id));

  return (
    <div className="flex-1 flex flex-col bg-white">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-black">{currentChat.name}</h1>
            <div className="flex items-center gap-2 text-gray-600">
              <span>
                {currentChat.messages.length} message{currentChat.messages.length !== 1 ? 's' : ''}
              </span>
              {selectedDbs.length > 0 && (
                <>
                  <span>•</span>
                  <div className="flex items-center gap-2 flex-wrap">
                    {selectedDbs.map(db => (
                      <div key={db.id} className="flex items-center gap-1">
                        <div className={`w-2 h-2 rounded-full ${
                          db.connected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                        }`} />
                        <span className="text-xs">{db.name}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8 bg-gradient-to-b from-white to-slate-50">
        <div className="max-w-4xl mx-auto space-y-6">
          {currentChat.messages.map(message => (
            <div key={message.id}>
              <div
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-6 py-4 shadow-sm ${
                    message.sender === 'user'
                      ? 'bg-black text-white'
                      : 'bg-white text-black border border-slate-200'
                  }`}
                >
                  {message.dbContext && message.sender === 'user' && (
                    <div className="flex flex-wrap items-center gap-2 text-xs text-gray-300 mb-2 pb-2 border-b border-gray-700">
                      <Database className="h-3 w-3" />
                      {message.dbContext.map((db, idx) => (
                        <Badge key={idx} variant="secondary" className="bg-gray-700 text-gray-200 text-xs">
                          {db}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <p>{message.text}</p>
                  <p
                    className={`text-xs mt-2 ${
                      message.sender === 'user' ? 'text-gray-300' : 'text-gray-500'
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>

              {/* Artifact Card */}
              {message.artifact && (
                <div className="flex justify-start mt-3">
                  <button
                    onClick={() => onArtifactClick(message.artifact!)}
                    className="max-w-[75%] bg-gradient-to-br from-purple-50 to-blue-50 border-2 border-purple-200 rounded-2xl p-5 shadow-md hover:shadow-xl transition-all duration-200 group"
                  >
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-purple-500 rounded-xl text-white group-hover:scale-110 transition-transform">
                        <FileText className="h-6 w-6" />
                      </div>
                      <div className="flex-1 text-left">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-black">Report Artifact</h3>
                          <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-full">
                            Interactive
                          </span>
                        </div>
                        <p className="text-purple-900 mb-2">{message.artifact.name}</p>
                        <p className="text-xs text-purple-600">
                          Click to view in side panel →
                        </p>
                      </div>
                    </div>
                  </button>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-slate-200 px-6 py-4 shadow-lg">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="space-y-3">
            {/* Database Multi-Selector */}
            {dbConnections.length > 0 && (
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-slate-500" />
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-auto min-w-[250px] h-9 rounded-lg border-slate-200 text-sm justify-between"
                    >
                      {selectedDbIds.length === 0 ? (
                        <span className="text-slate-500">Select databases...</span>
                      ) : (
                        <span>
                          {selectedDbIds.length} database{selectedDbIds.length !== 1 ? 's' : ''} selected
                        </span>
                      )}
                      <ChevronDown className="h-4 w-4 ml-2 text-slate-500" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80 p-4" align="start">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm text-black">Select Data Sources</h4>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleSelectAll}
                            className="h-7 text-xs"
                          >
                            All
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleDeselectAll}
                            className="h-7 text-xs"
                          >
                            None
                          </Button>
                        </div>
                      </div>
                      
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {dbConnections.map(db => (
                          <div
                            key={db.id}
                            className="flex items-center space-x-3 p-2 hover:bg-slate-50 rounded-lg cursor-pointer"
                            onClick={() => handleToggleDb(db.id)}
                          >
                            <Checkbox
                              checked={selectedDbIds.includes(db.id)}
                              onCheckedChange={() => handleToggleDb(db.id)}
                            />
                            <div className="flex-1 flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${
                                  db.connected ? 'bg-green-500' : 'bg-gray-400'
                                }`} />
                                <div>
                                  <p className="text-sm text-black">{db.name}</p>
                                  <p className="text-xs text-slate-500">{db.type}</p>
                                </div>
                              </div>
                              {db.isDefault && (
                                <Badge variant="secondary" className="text-xs">
                                  Default
                                </Badge>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>

                {/* Selected DB Tags */}
                {selectedDbs.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    {selectedDbs.map(db => (
                      <Badge
                        key={db.id}
                        variant="secondary"
                        className="flex items-center gap-1 bg-slate-100 text-slate-700 cursor-pointer hover:bg-slate-200"
                        onClick={() => handleToggleDb(db.id)}
                      >
                        <div className={`w-1.5 h-1.5 rounded-full ${
                          db.connected ? 'bg-green-500' : 'bg-gray-400'
                        }`} />
                        {db.name}
                        <span className="ml-1 text-slate-400">×</span>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Message Input */}
            <div className="flex gap-3">
              <Input
                type="text"
                placeholder={selectedDbs.length > 0
                  ? `Query ${selectedDbs.length} database${selectedDbs.length !== 1 ? 's' : ''}...`
                  : "Type your message..."}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="flex-1 h-12 rounded-xl border-slate-200 focus:border-black focus:ring-black"
              />
              <Button
                type="submit"
                className="h-12 px-6 bg-black hover:bg-gray-800 text-white rounded-xl transition-all duration-200 shadow-md hover:shadow-lg"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}