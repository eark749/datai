import { useState } from 'react';
import { ChatSidebar } from './ChatSidebar';
import { ChatArea } from './ChatArea';
import { ArtifactPanel } from './ArtifactPanel';
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from './ui/tooltip';
import { Button } from './ui/button';
import { PanelLeft, PanelLeftClose } from 'lucide-react';

interface ChatInterfaceProps {
  onLogout: () => void;
}

export interface ChatSession {
  id: string;
  name: string;
  timestamp: Date;
  preview: string;
  messages: Message[];
  activeDbId?: string; // Track which DB is active for this chat
  isPinned?: boolean; // Pin important chats
  isArchived?: boolean; // Archive old chats
}

export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  artifact?: Artifact;
  dbContext?: string[]; // Array of DB names used for this query
}

export interface Artifact {
  id: string;
  name: string;
  type: 'report';
  htmlContent: string;
  thumbnail?: string;
}

export interface DatabaseConnection {
  id: string;
  name: string; // User-friendly name for the connection
  type: string;
  host: string;
  port: string;
  username: string;
  password: string;
  database: string;
  connected: boolean;
  isDefault: boolean;
}

export function ChatInterface({ onLogout }: ChatInterfaceProps) {
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([
    {
      id: '1',
      name: 'Welcome Chat',
      timestamp: new Date(),
      preview: 'Hello! How can I help you today?',
      messages: [
        {
          id: '1',
          text: 'Hello! How can I help you today?',
          sender: 'bot',
          timestamp: new Date(),
        },
      ],
      isPinned: false,
      isArchived: false,
    },
  ]);

  const [currentChatId, setCurrentChatId] = useState('1');
  const [dbConnections, setDbConnections] = useState<DatabaseConnection[]>([]);
  const [openArtifacts, setOpenArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);
  const [showArtifactPanel, setShowArtifactPanel] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const currentChat = chatSessions.find(chat => chat.id === currentChatId);

  const handleNewChat = () => {
    const newChat: ChatSession = {
      id: Date.now().toString(),
      name: `Chat ${chatSessions.length + 1}`,
      timestamp: new Date(),
      preview: 'New conversation',
      messages: [
        {
          id: Date.now().toString(),
          text: 'Hello! How can I help you today?',
          sender: 'bot',
          timestamp: new Date(),
        },
      ],
      isPinned: false,
      isArchived: false,
    };
    setChatSessions(prev => [...prev, newChat]);
    setCurrentChatId(newChat.id);
  };

  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId);
  };

  const handleDeleteChat = (chatId: string) => {
    // Don't allow deleting the last chat
    if (chatSessions.length === 1) {
      return;
    }

    // If deleting current chat, select another one
    if (currentChatId === chatId) {
      const remainingChats = chatSessions.filter(chat => chat.id !== chatId);
      setCurrentChatId(remainingChats[0].id);
    }

    // Remove the chat
    setChatSessions(prev => prev.filter(chat => chat.id !== chatId));
  };

  const handleSendMessage = (text: string, selectedDbIds?: string[]) => {
    if (!currentChat) return;

    const selectedDbs = selectedDbIds 
      ? dbConnections.filter(db => selectedDbIds.includes(db.id))
      : [];

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
      dbContext: selectedDbs.length > 0 
        ? selectedDbs.map(db => `${db.name} (${db.type})`)
        : undefined,
    };

    // Update current chat with new message
    setChatSessions(prev =>
      prev.map(chat =>
        chat.id === currentChatId
          ? {
              ...chat,
              messages: [...chat.messages, userMessage],
              preview: text.substring(0, 50),
              activeDbId: selectedDbIds?.[0] || chat.activeDbId,
            }
          : chat
      )
    );

    // Simulate bot response
    setTimeout(() => {
      // Check if user requested a report (for demo purposes)
      const userRequestedReport = text.toLowerCase().includes('report') || 
                                   text.toLowerCase().includes('dashboard') ||
                                   text.toLowerCase().includes('analytics');
      
      // Simulate backend response
      const dbContextMessage = selectedDbs.length > 0
        ? selectedDbs.length === 1
          ? `Query processed with ${selectedDbs[0].name} (${selectedDbs[0].type}) database context.`
          : `Query processed across ${selectedDbs.length} databases: ${selectedDbs.map(db => db.name).join(', ')}. Results aggregated successfully!`
        : 'This is a demo response. Select databases to enable context-aware queries.';

      const mockBackendResponse = {
        message: dbContextMessage,
        artifact: (Math.random() > 0.7 || userRequestedReport) ? {
          id: Date.now().toString(),
          name: 'Sales Dashboard Report',
          type: 'report' as const,
          htmlContent: generateMockReport(),
        } : undefined,
      };

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: mockBackendResponse.artifact 
          ? "I've generated a sales dashboard report for you. Click the artifact below to view it in the side panel."
          : mockBackendResponse.message,
        sender: 'bot',
        timestamp: new Date(),
        artifact: mockBackendResponse.artifact,
      };

      setChatSessions(prev =>
        prev.map(chat =>
          chat.id === currentChatId
            ? { ...chat, messages: [...chat.messages, botMessage] }
            : chat
        )
      );
    }, 1000);
  };

  const handleAddDbConnection = (connection: Omit<DatabaseConnection, 'id'>) => {
    const newConnection: DatabaseConnection = {
      ...connection,
      id: Date.now().toString(),
    };
    setDbConnections(prev => [...prev, newConnection]);
  };

  const handleUpdateDbConnection = (id: string, updates: Partial<DatabaseConnection>) => {
    setDbConnections(prev =>
      prev.map(conn => (conn.id === id ? { ...conn, ...updates } : conn))
    );
  };

  const handleDeleteDbConnection = (id: string) => {
    setDbConnections(prev => prev.filter(conn => conn.id !== id));
  };

  const handleSetDefaultDb = (id: string) => {
    setDbConnections(prev =>
      prev.map(conn => {
        // If clicking the current default, unset it
        if (conn.id === id && conn.isDefault) {
          return { ...conn, isDefault: false };
        }
        // Otherwise, set this one as default and unset others
        return { ...conn, isDefault: conn.id === id };
      })
    );
  };

  const handleArtifactClick = (artifact: Artifact) => {
    // Check if artifact is already open
    const existingArtifact = openArtifacts.find(a => a.id === artifact.id);
    
    if (!existingArtifact) {
      // Add new artifact to the list
      setOpenArtifacts(prev => [...prev, artifact]);
    }
    
    // Set as active and show panel
    setActiveArtifactId(artifact.id);
    setShowArtifactPanel(true);
  };

  const handleCloseArtifact = (artifactId: string) => {
    setOpenArtifacts(prev => {
      const filtered = prev.filter(a => a.id !== artifactId);
      
      // If closing the active artifact, switch to another one
      if (artifactId === activeArtifactId) {
        if (filtered.length > 0) {
          setActiveArtifactId(filtered[0].id);
        } else {
          setShowArtifactPanel(false);
          setActiveArtifactId(null);
        }
      }
      
      return filtered;
    });
  };

  const handleCloseAllArtifacts = () => {
    setOpenArtifacts([]);
    setActiveArtifactId(null);
    setShowArtifactPanel(false);
  };

  const handleRenameArtifact = (artifactId: string, newName: string) => {
    setOpenArtifacts(prev =>
      prev.map(artifact =>
        artifact.id === artifactId ? { ...artifact, name: newName } : artifact
      )
    );
    
    // Also update in chat messages
    setChatSessions(prev =>
      prev.map(chat => ({
        ...chat,
        messages: chat.messages.map(msg =>
          msg.artifact?.id === artifactId
            ? { ...msg, artifact: { ...msg.artifact, name: newName } }
            : msg
        ),
      }))
    );
  };

  const handleTogglePin = (chatId: string) => {
    setChatSessions(prev =>
      prev.map(chat =>
        chat.id === chatId ? { ...chat, isPinned: !chat.isPinned } : chat
      )
    );
  };

  const handleToggleArchive = (chatId: string) => {
    setChatSessions(prev =>
      prev.map(chat =>
        chat.id === chatId ? { ...chat, isArchived: !chat.isArchived } : chat
      )
    );
  };

  return (
    <div className="h-screen bg-gray-50 flex overflow-hidden">
      {!isSidebarCollapsed && (
        <ChatSidebar
          chatSessions={chatSessions}
          currentChatId={currentChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
          onLogout={onLogout}
          dbConnections={dbConnections}
          onAddDbConnection={handleAddDbConnection}
          onUpdateDbConnection={handleUpdateDbConnection}
          onDeleteDbConnection={handleDeleteDbConnection}
          onSetDefaultDb={handleSetDefaultDb}
          onTogglePin={handleTogglePin}
          onToggleArchive={handleToggleArchive}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={setIsSidebarCollapsed}
        />
      )}

      {/* Toggle Button - Always visible with fixed positioning */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              variant="outline"
              size="sm"
              className="fixed top-4 left-4 z-50 h-10 w-10 p-0 bg-white border-slate-300 shadow-lg hover:shadow-xl transition-all duration-300 rounded-xl"
              aria-label={isSidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
            >
              {isSidebarCollapsed ? (
                <PanelLeft className="h-5 w-5" />
              ) : (
                <PanelLeftClose className="h-5 w-5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{isSidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <div className={`flex-1 flex min-w-0 transition-all duration-300 ${
        isSidebarCollapsed ? 'ml-16' : 'ml-0'
      }`}>
        <ChatArea
          currentChat={currentChat}
          onSendMessage={handleSendMessage}
          dbConnections={dbConnections}
          onArtifactClick={handleArtifactClick}
        />

        {showArtifactPanel && activeArtifactId && openArtifacts.length > 0 && (
          <ArtifactPanel
            artifacts={openArtifacts}
            activeArtifactId={activeArtifactId}
            onClose={handleCloseArtifact}
            onCloseAll={handleCloseAllArtifacts}
            onSwitchArtifact={setActiveArtifactId}
            onRenameArtifact={handleRenameArtifact}
          />
        )}
      </div>
    </div>
  );
}

function generateMockReport(): string {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: system-ui; padding: 20px; background: white; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: #f8f9fa; padding: 20px; border-radius: 12px; border-left: 4px solid #667eea; }
        .metric-value { font-size: 32px; font-weight: bold; color: #667eea; margin: 10px 0; }
        .metric-label { color: #6c757d; font-size: 14px; }
        .chart-container { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }
        th { background: #f8f9fa; font-weight: 600; }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>Sales Dashboard Report</h1>
        <p>Generated on ${new Date().toLocaleDateString()}</p>
      </div>
      
      <div class="metric-grid">
        <div class="metric-card">
          <div class="metric-label">Total Revenue</div>
          <div class="metric-value">$284,590</div>
          <div style="color: #28a745; font-size: 12px;">↑ 12.5% from last month</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Orders</div>
          <div class="metric-value">1,842</div>
          <div style="color: #28a745; font-size: 12px;">↑ 8.2% from last month</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Order Value</div>
          <div class="metric-value">$154.52</div>
          <div style="color: #dc3545; font-size: 12px;">↓ 2.1% from last month</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Active Customers</div>
          <div class="metric-value">892</div>
          <div style="color: #28a745; font-size: 12px;">↑ 15.3% from last month</div>
        </div>
      </div>

      <div class="chart-container">
        <h3>Top Products</h3>
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Units Sold</th>
              <th>Revenue</th>
              <th>Growth</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Premium Widget Pro</td>
              <td>342</td>
              <td>$68,400</td>
              <td style="color: #28a745;">+18%</td>
            </tr>
            <tr>
              <td>Standard Widget</td>
              <td>521</td>
              <td>$52,100</td>
              <td style="color: #28a745;">+12%</td>
            </tr>
            <tr>
              <td>Widget Accessories</td>
              <td>789</td>
              <td>$39,450</td>
              <td style="color: #28a745;">+25%</td>
            </tr>
            <tr>
              <td>Basic Widget</td>
              <td>412</td>
              <td>$24,720</td>
              <td style="color: #dc3545;">-5%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </body>
    </html>
  `;
}