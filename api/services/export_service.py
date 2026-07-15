"""
Export service for generating CSV exports.
"""
import csv
import io
from typing import List
from datetime import datetime

from models.prospect_db import ProspectDB
from models.campaign import Campaign


class ExportService:
    """Service for exporting data to CSV format."""
    
    def export_prospects_to_csv(self, prospects: List[ProspectDB]) -> str:
        """
        Export prospects to CSV format.
        
        Args:
            prospects: List of prospects to export
            
        Returns:
            CSV data as string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Write header
        writer.writerow([
            'ID',
            'Nom',
            'Email',
            'Téléphone',
            'Adresse',
            'Ville',
            'Catégorie',
            'Source',
            'Site Web',
            'Confiance',
            'Date de création'
        ])
        
        # Write data
        for prospect in prospects:
            writer.writerow([
                prospect.id,
                prospect.name,
                prospect.email or '',
                prospect.phone or '',
                prospect.address or '',
                prospect.city or '',
                prospect.category,
                prospect.source,
                prospect.website or '',
                prospect.confidence,
                prospect.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return output.getvalue()
    
    def export_campaign_to_csv(
        self,
        campaign: Campaign,
        include_prospects: bool = True
    ) -> str:
        """
        Export campaign to CSV format.
        
        Args:
            campaign: Campaign to export
            include_prospects: Whether to include prospect details
            
        Returns:
            CSV data as string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Write campaign header
        writer.writerow(['Campagne', campaign.name])
        writer.writerow(['Description', campaign.description or ''])
        writer.writerow(['Statut', campaign.status])
        writer.writerow(['Date de création', campaign.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Nombre de prospects', len(campaign.prospects)])
        writer.writerow([])  # Empty line
        
        if include_prospects and campaign.prospects:
            # Write prospects header
            writer.writerow([
                'ID Prospect',
                'Nom',
                'Email',
                'Téléphone',
                'Ville',
                'Catégorie',
                'Source'
            ])
            
            # Write prospects data
            for prospect in campaign.prospects:
                writer.writerow([
                    prospect.id,
                    prospect.name,
                    prospect.email or '',
                    prospect.phone or '',
                    prospect.city or '',
                    prospect.category,
                    prospect.source
                ])
        
        return output.getvalue()
    
    def export_campaigns_summary_to_csv(self, campaigns: List[Campaign]) -> str:
        """
        Export campaigns summary to CSV format.
        
        Args:
            campaigns: List of campaigns to export
            
        Returns:
            CSV data as string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Write header
        writer.writerow([
            'ID',
            'Nom',
            'Description',
            'Statut',
            'Nombre de prospects',
            'Date de création',
            'Date de modification'
        ])
        
        # Write data
        for campaign in campaigns:
            writer.writerow([
                campaign.id,
                campaign.name,
                campaign.description or '',
                campaign.status,
                len(campaign.prospects),
                campaign.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                campaign.updated_at.strftime('%Y-%m-%d %H:%M:%S') if campaign.updated_at else ''
            ])
        
        return output.getvalue()


# Singleton instance
export_service = ExportService()

