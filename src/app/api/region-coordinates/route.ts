import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const yamlPath = path.join(process.cwd(), 'backend', 'utils', 'region_coordinates.yaml');
    const fileContents = fs.readFileSync(yamlPath, 'utf8');
    const data = yaml.load(fileContents) as Record<string, { lat: number; lng: number }>;
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error loading region coordinates:', error);
    return NextResponse.json({ error: 'Failed to load region coordinates' }, { status: 500 });
  }
}