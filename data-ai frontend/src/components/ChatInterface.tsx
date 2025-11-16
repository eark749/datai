import { useState, useEffect } from 'react';
import { ChatSidebar } from './ChatSidebar';
import { ChatArea } from './ChatArea';
import { ArtifactPanel } from './ArtifactPanel';
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from './ui/tooltip';
import { Button } from './ui/button';
import { PanelLeft, PanelLeftClose } from 'lucide-react';
import { 
  createChat, 
  listChats, 
  getChat, 
  deleteChat as deleteChatAPI, 
  archiveChat as archiveChatAPI,
  sendQuery
} from '../api/chat.service';
import {
  listDatabaseConnections,
  createDatabaseConnection,
  updateDatabaseConnection,
  deleteDatabaseConnection as deleteDatabaseConnectionAPI,
  DatabaseConnectionRequest
} from '../api/database.service';
import { AxiosError } from 'axios';

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
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>('');
  const [dbConnections, setDbConnections] = useState<DatabaseConnection[]>([]);
  const [openArtifacts, setOpenArtifacts] = useState<Artifact[]>([]);
  const [activeArtifactId, setActiveArtifactId] = useState<string | null>(null);
  const [showArtifactPanel, setShowArtifactPanel] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);

  const currentChat = chatSessions.find(chat => chat.id === currentChatId);

  // Load chats and databases on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoading(true);
        
        // Load databases FIRST
        const dbs = await listDatabaseConnections();
        const formattedDbs = dbs.map(db => ({
          id: db.id,
          name: db.name,
          type: db.db_type,
          host: db.host,
          port: db.port.toString(),
          username: db.username,
          password: '', // Don't store password
          database: db.database_name,
          connected: true, // Assume connected if it exists
          isDefault: false, // Will be set by user
        }));
        setDbConnections(formattedDbs);

        // Load chats AFTER databases are loaded
        const chats = await listChats();
        if (chats.length > 0) {
          const formattedChats = chats.map(chat => ({
            id: chat.id,
            name: chat.title || 'Untitled Chat',
            timestamp: new Date(chat.created_at),
            preview: 'Chat conversation',
            messages: [], // Will load when selected
            activeDbId: chat.db_connection_id,
            isPinned: false,
            isArchived: chat.is_archived,
          }));
          setChatSessions(formattedChats);
          setCurrentChatId(formattedChats[0].id);
          // Load the first chat's messages
          await loadChatMessages(formattedChats[0].id);
        } else {
          // Create a new chat if none exists (with first available DB)
          const defaultDbId = formattedDbs.length > 0 ? formattedDbs[0].id : undefined;
          await createNewChatWithDb(defaultDbId);
        }
      } catch (error) {
        console.error('Error loading data:', error);
        if (error instanceof AxiosError && error.response?.status === 401) {
          // Token expired, logout
          onLogout();
        } else {
          // Create a default chat on error (without DB if not loaded)
          await createNewChatWithDb(undefined);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  // Load chat messages when selected
  const loadChatMessages = async (chatId: string) => {
    try {
      const chat = await getChat(chatId);
      const messages: Message[] = chat.messages?.map(msg => ({
        id: msg.id,
        text: msg.content,
        sender: msg.role === 'user' ? 'user' : 'bot',
        timestamp: new Date(msg.created_at),
        artifact: msg.dashboard_html ? {
          id: msg.id + '_artifact',
          name: 'Dashboard Report',
          type: 'report',
          htmlContent: msg.dashboard_html,
        } : undefined,
      })) || [];

      setChatSessions(prev =>
        prev.map(c =>
          c.id === chatId ? { ...c, messages, preview: messages[messages.length - 1]?.text || 'Empty chat' } : c
        )
      );
    } catch (error) {
      console.error('Error loading chat messages:', error);
    }
  };

  // Helper function to create a new chat with optional database ID
  const createNewChatWithDb = async (dbId?: string) => {
    try {
      const newChatResponse = await createChat({ 
        title: `Chat ${chatSessions.length + 1}`,
        db_connection_id: dbId
      });
      
      const newChat: ChatSession = {
        id: newChatResponse.id,
        name: newChatResponse.title,
        timestamp: new Date(newChatResponse.created_at),
        preview: 'New conversation',
        messages: [],
        isPinned: false,
        isArchived: false,
        activeDbId: dbId,
      };
      setChatSessions(prev => [newChat, ...prev]);
      setCurrentChatId(newChat.id);
    } catch (error) {
      console.error('Error creating chat:', error);
      alert('Failed to create new chat. Please try again.');
    }
  };

  const handleNewChat = async () => {
    // Use first available database when creating chat
    const defaultDbId = dbConnections.length > 0 ? dbConnections[0].id : undefined;
    await createNewChatWithDb(defaultDbId);
  };

  const handleSelectChat = async (chatId: string) => {
    setCurrentChatId(chatId);
    // Load messages if not already loaded
    const chat = chatSessions.find(c => c.id === chatId);
    if (chat && chat.messages.length === 0) {
      await loadChatMessages(chatId);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    // Don't allow deleting the last chat
    if (chatSessions.length === 1) {
      return;
    }

    try {
      await deleteChatAPI(chatId);

      // If deleting current chat, select another one
      if (currentChatId === chatId) {
        const remainingChats = chatSessions.filter(chat => chat.id !== chatId);
        setCurrentChatId(remainingChats[0].id);
      }

      // Remove the chat
      setChatSessions(prev => prev.filter(chat => chat.id !== chatId));
    } catch (error) {
      console.error('Error deleting chat:', error);
      alert('Failed to delete chat. Please try again.');
    }
  };

  const handleSendMessage = async (text: string, selectedDbIds?: string[]) => {
    if (!currentChat || isSending) return;

    const selectedDbs = selectedDbIds 
      ? dbConnections.filter(db => selectedDbIds.includes(db.id))
      : [];

    const userMessage: Message = {
      id: 'temp_' + Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
      dbContext: selectedDbs.length > 0 
        ? selectedDbs.map(db => `${db.name} (${db.type})`)
        : undefined,
    };

    // Add user message immediately
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

    setIsSending(true);

    try {
      // Send query to backend
      const response = await sendQuery({
        message: text,
        chat_id: currentChatId,
        db_connection_id: selectedDbIds?.[0],
      });

      // Create bot response message
      const botMessage: Message = {
        id: response.message_id,
        text: response.assistant_message,
        sender: 'bot',
        timestamp: new Date(),
        artifact: response.dashboard_html ? {
          id: response.message_id + '_artifact',
          name: 'Dashboard Report',
          type: 'report',
          htmlContent: response.dashboard_html,
        } : undefined,
      };

      // Add bot response
      setChatSessions(prev =>
        prev.map(chat =>
          chat.id === currentChatId
            ? { ...chat, messages: [...chat.messages, botMessage] }
            : chat
        )
      );
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Determine error message
      let errorText = 'Sorry, I encountered an error processing your request. Please try again.';
      
      if (error instanceof AxiosError) {
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          errorText = '⏱️ Request timed out. Dashboard generation can take up to 2 minutes. Please try again.';
        } else if (error.response?.data?.detail) {
          errorText = `Error: ${error.response.data.detail}`;
        }
      }
      
      // Add error message
      const errorMessage: Message = {
        id: 'error_' + Date.now().toString(),
        text: errorText,
        sender: 'bot',
        timestamp: new Date(),
      };

      setChatSessions(prev =>
        prev.map(chat =>
          chat.id === currentChatId
            ? { ...chat, messages: [...chat.messages, errorMessage] }
            : chat
        )
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleAddDbConnection = async (connection: Omit<DatabaseConnection, 'id'>) => {
    try {
      const dbRequest: DatabaseConnectionRequest = {
        name: connection.name,
        db_type: connection.type.toLowerCase(),
        host: connection.host,
        port: parseInt(connection.port) || 5432,
        database_name: connection.database,
        username: connection.username,
        password: connection.password,
      };

      const newDb = await createDatabaseConnection(dbRequest);
      const newConnection: DatabaseConnection = {
        id: newDb.id,
        name: newDb.name,
        type: newDb.db_type,
        host: newDb.host,
        port: newDb.port.toString(),
        username: newDb.username,
        password: '',
        database: newDb.database_name,
        connected: true,
        isDefault: connection.isDefault,
      };
      setDbConnections(prev => [...prev, newConnection]);
    } catch (error) {
      console.error('Error adding database connection:', error);
      throw error;
    }
  };

  const handleUpdateDbConnection = async (id: string, updates: Partial<DatabaseConnection>) => {
    try {
      if (updates.name || updates.host || updates.port || updates.database || updates.username || updates.password) {
        const dbRequest: Partial<DatabaseConnectionRequest> = {};
        if (updates.name) dbRequest.name = updates.name;
        if (updates.type) dbRequest.db_type = updates.type.toLowerCase();
        if (updates.host) dbRequest.host = updates.host;
        if (updates.port) dbRequest.port = parseInt(updates.port);
        if (updates.database) dbRequest.database_name = updates.database;
        if (updates.username) dbRequest.username = updates.username;
        if (updates.password) dbRequest.password = updates.password;

        await updateDatabaseConnection(id, dbRequest);
      }

      setDbConnections(prev =>
        prev.map(conn => (conn.id === id ? { ...conn, ...updates } : conn))
      );
    } catch (error) {
      console.error('Error updating database connection:', error);
      throw error;
    }
  };

  const handleDeleteDbConnection = async (id: string) => {
    try {
      console.log('ChatInterface: Starting delete for connection:', id);
      console.log('ChatInterface: Current connections:', dbConnections.map(c => c.id));
      
      await deleteDatabaseConnectionAPI(id);
      
      console.log('ChatInterface: API delete successful');
      
      // Create completely new array to force re-render
      const newConnections = dbConnections.filter(conn => conn.id !== id);
      console.log('ChatInterface: New connections array:', newConnections.map(c => c.id));
      
      setDbConnections(newConnections);
      console.log('ChatInterface: State update triggered');
    } catch (error) {
      console.error('ChatInterface: Error deleting database connection:', error);
      throw error;
    }
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

  const handleToggleArchive = async (chatId: string) => {
    try {
      await archiveChatAPI(chatId);
      setChatSessions(prev =>
        prev.map(chat =>
          chat.id === chatId ? { ...chat, isArchived: !chat.isArchived } : chat
        )
      );
    } catch (error) {
      console.error('Error archiving chat:', error);
      alert('Failed to archive chat. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

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
